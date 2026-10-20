"""
In-Azure orchestrator for the sharded weekly run (JOB_TYPE=orchestrate).

Why this exists: GitHub Actions can't supervise a multi-hour run (the job /
Azure login dies at ~1h), so the workflow now only *starts this one small
container* and leaves. This container then drives the whole pipeline through
the Azure Container Instances API, using its managed identity:

    prepare   (1 container, 2 vCPU)    attrition + one GDELT download
    shards    (N containers, 1 vCPU)   biographies + turnout + vote, in parallel
    finalize  (1 container, 4 vCPU)    merge shards, MRP, aggregates

Each stage is the SAME worker image started with a different JOB_TYPE (see
run_job.py); this module only starts containers, waits for them, checks exit
codes, retries failed shards, and cleans up.

Retrying a shard is safe and cheap: shards resume from their own checkpoint
blob, so a retried container picks up where the failed one stopped.

vCPU budget (10 total): this orchestrator 1 + 9 shards = 10 at peak,
orchestrator 1 + prepare 2 = 3, orchestrator 1 + finalize 4 = 5. Stages never
overlap, so the peak is the shard stage.

Required env on the orchestrator container (see weekly-job.yml):
    AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, ACI_LOCATION (default westeurope)
    WORKER_IMAGE, ACR_LOGIN_SERVER, ACR_USERNAME, ACR_PASSWORD
  and ONE way to authenticate to Azure (needs Contributor on the resource group):
    - AZURE_TENANT_ID + AZURE_CLIENT_ID + AZURE_CLIENT_SECRET   a service principal
      (e.g. the one the GitHub workflow already uses, with a client secret added), or
    - ORCH_IDENTITY_CLIENT_ID   client id of a user-assigned managed identity
    The service principal is used if AZURE_CLIENT_SECRET is set.
plus the pipeline env it forwards to the stages (storage / OpenAI / Cohere keys, ...).
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import azure_storage_utils as storage
from .generate_panel_results import iso_week_label, _load_country_info

logger = logging.getLogger(__name__)

CONTAINER_NAME = "worker"
POLL_SECONDS = 30
MAX_SHARD_ATTEMPTS = 3

# Forwarded to child containers as plain env vars / secure env vars.
PLAIN_ENV_KEYS = [
    "ENV", "COUNTRIES", "BLOB_CONTAINER_NAME", "COMPUTE_MRP_DRAWS",
    "US_POLLS_BLOB_CONTAINER", "US_POLLS_OUTPUT_BLOB_NAME",
]
SECRET_ENV_KEYS = [
    "AZURE_STORAGE_CONNECTION_STRING", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_MODEL",
    "AZURE_OPENAI_BASE_URL", "COHERE_API_KEY",
]


@dataclass(frozen=True)
class Resources:
    cpu: float
    memory_gb: float


PREPARE_RESOURCES = Resources(cpu=2, memory_gb=4)
SHARD_RESOURCES = Resources(cpu=1, memory_gb=2)
FINALIZE_RESOURCES = Resources(cpu=4, memory_gb=16)   # R / MRP, same as the old single worker


class StageFailed(RuntimeError):
    pass


# ───────────────────────────── ACI wrapper ─────────────────────────────────

def _need(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(f"Missing required environment variable for the orchestrator: {name}")
    return val


class _Aci:
    """Thin wrapper over the Azure Container Instances management API."""

    def __init__(self) -> None:
        from azure.mgmt.containerinstance import ContainerInstanceManagementClient

        self.rg = _need("AZURE_RESOURCE_GROUP")
        self.location = os.environ.get("ACI_LOCATION", "westeurope")
        self.image = _need("WORKER_IMAGE")
        self.registry = (_need("ACR_LOGIN_SERVER"), _need("ACR_USERNAME"), _need("ACR_PASSWORD"))
        if os.environ.get("AZURE_CLIENT_SECRET"):
            from azure.identity import ClientSecretCredential
            credential = ClientSecretCredential(
                tenant_id=_need("AZURE_TENANT_ID"),
                client_id=_need("AZURE_CLIENT_ID"),
                client_secret=os.environ["AZURE_CLIENT_SECRET"],
            )
        else:
            from azure.identity import ManagedIdentityCredential
            client_id = os.environ.get("ORCH_IDENTITY_CLIENT_ID")
            credential = ManagedIdentityCredential(client_id=client_id) if client_id else ManagedIdentityCredential()
        self.client = ContainerInstanceManagementClient(credential, _need("AZURE_SUBSCRIPTION_ID"))

    def start(self, name: str, res: Resources, env: dict[str, str], secure_env: dict[str, str]) -> None:
        from azure.mgmt.containerinstance.models import (
            Container, ContainerGroup, EnvironmentVariable, ImageRegistryCredential,
            ResourceRequests, ResourceRequirements,
        )
        self.delete(name)  # clear any leftover from a previous/killed run (also frees its vCPUs)
        container = Container(
            name=CONTAINER_NAME,
            image=self.image,
            resources=ResourceRequirements(requests=ResourceRequests(cpu=res.cpu, memory_in_gb=res.memory_gb)),
            environment_variables=(
                [EnvironmentVariable(name=k, value=v) for k, v in env.items()]
                + [EnvironmentVariable(name=k, secure_value=v) for k, v in secure_env.items()]
            ),
        )
        group = ContainerGroup(
            location=self.location,
            containers=[container],
            os_type="Linux",
            restart_policy="Never",
            image_registry_credentials=[
                ImageRegistryCredential(server=self.registry[0], username=self.registry[1], password=self.registry[2])
            ],
        )
        self.client.container_groups.begin_create_or_update(self.rg, name, group).result()

    def poll(self, name: str) -> tuple[str, int | None]:
        """(state, exit_code). state is Waiting / Running / Terminated / Missing."""
        from azure.core.exceptions import ResourceNotFoundError
        try:
            group = self.client.container_groups.get(self.rg, name)
        except ResourceNotFoundError:
            return "Missing", None
        view = group.containers[0].instance_view if group.containers else None
        current = view.current_state if view else None
        if current is None or current.state is None:
            return "Waiting", None
        return current.state, current.exit_code

    def tail_logs(self, name: str, lines: int = 80) -> str:
        try:
            return self.client.containers.list_logs(self.rg, name, CONTAINER_NAME, tail=lines).content or ""
        except Exception as exc:  # noqa: BLE001
            return f"(could not fetch logs: {exc})"

    def delete(self, name: str) -> None:
        from azure.core.exceptions import ResourceNotFoundError
        try:
            self.client.container_groups.begin_delete(self.rg, name).result()
        except ResourceNotFoundError:
            pass


# ───────────────────────────── stage runners ───────────────────────────────

def _secrets(keys: list[str] | None = None) -> dict[str, str]:
    return {k: os.environ[k] for k in (keys or SECRET_ENV_KEYS) if os.environ.get(k)}


def _run_single_stage(aci, name, res, env, secure_env, deadline, created: set) -> None:
    created.add(name)
    logger.info("Starting %s (%.0f vCPU / %.0f GB)...", name, res.cpu, res.memory_gb)
    aci.start(name, res, env, secure_env)
    while True:
        state, code = aci.poll(name)
        if state in ("Terminated", "Missing"):
            break
        if time.time() > deadline:
            raise TimeoutError(f"{name} did not finish before the orchestrator deadline.")
        time.sleep(POLL_SECONDS)
    if state != "Terminated" or code != 0:
        logger.error("%s failed (state=%s, exit code=%s). Last log lines:\n%s", name, state, code, aci.tail_logs(name))
        raise StageFailed(f"{name} failed (state={state}, exit code={code}).")
    aci.delete(name)
    logger.info("%s finished OK.", name)


def _run_shards(aci, num_shards, shard_env, secure_env, deadline, created: set) -> None:
    attempts = {i: 0 for i in range(num_shards)}
    running: dict[int, str] = {}
    failed: list[int] = []

    def launch(i: int) -> None:
        attempts[i] += 1
        name = f"weekly-shard-aci-{i}"
        created.add(name)
        aci.start(name, SHARD_RESOURCES, {**shard_env, "JOB_TYPE": "panel_shard", "SHARD_INDEX": str(i)}, secure_env)
        running[i] = name
        logger.info("Shard %d/%d started (attempt %d).", i + 1, num_shards, attempts[i])

    for i in range(num_shards):
        launch(i)

    finished = 0
    while running:
        time.sleep(POLL_SECONDS)
        for i, name in list(running.items()):
            state, code = aci.poll(name)
            if state not in ("Terminated", "Missing"):
                continue
            del running[i]
            if state == "Terminated" and code == 0:
                aci.delete(name)
                finished += 1
                logger.info("Shard %d/%d finished OK (%d/%d done).", i + 1, num_shards, finished, num_shards)
                continue
            logger.error("Shard %d failed (state=%s, exit code=%s). Last log lines:\n%s", i + 1, state, code, aci.tail_logs(name))
            if attempts[i] < MAX_SHARD_ATTEMPTS:
                logger.warning("Retrying shard %d — it resumes from its checkpoint.", i + 1)
                launch(i)
            else:
                aci.delete(name)
                failed.append(i)
        if running and time.time() > deadline:
            raise TimeoutError(f"Shards {sorted(running)} did not finish before the orchestrator deadline.")

    if failed:
        raise StageFailed(
            f"Shard(s) {sorted(failed)} failed after {MAX_SHARD_ATTEMPTS} attempts. Their checkpoints are in blob "
            "storage — rerun the workflow and they resume from where they stopped."
        )


# ───────────────────────────── entry point ─────────────────────────────────

def run_orchestrator(
    countries: list[str],
    year: int,
    week: int,
    pipeline_job_type: str,
    num_shards: int,
    aci=None,
) -> None:
    """
    pipeline_job_type: "panel" | "mrp" | "both" — same meaning as the workflow's
    job_type input. Every stage is idempotent, so rerunning after a failure just
    resumes.
    """
    week_label = iso_week_label(year, week)
    target_week = f"{year}-{week:02d}"
    run_panel = pipeline_job_type in ("panel", "both")
    run_mrp = pipeline_job_type in ("mrp", "both")

    panel_countries = [c for c in countries if _load_country_info(c).get("question_id")]
    panel_done = all(storage.already_ran(c, "panel", week_label) for c in panel_countries)
    mrp_done = all(storage.already_ran(c, "mrp", week_label) for c in countries)

    final_types = []
    if run_panel and not panel_done:
        final_types.append("panel_merge")
    if run_mrp and not mrp_done:
        final_types.append("mrp")
    need_panel_stages = run_panel and not panel_done

    logger.info(
        "Orchestrating %s for %s: panel stages=%s, finalize=%s, shards=%d",
        week_label, countries, need_panel_stages, final_types or "none", num_shards,
    )
    if not need_panel_stages and not final_types:
        logger.info("Nothing to do — all requested stages already complete for %s.", week_label)
        return

    aci = aci or _Aci()
    base_env = {k: os.environ[k] for k in PLAIN_ENV_KEYS if os.environ.get(k)}
    base_env.update({"TARGET_WEEK": target_week, "NUM_SHARDS": str(num_shards)})
    deadline = time.time() + float(os.environ.get("ORCH_TIMEOUT_HOURS", "8")) * 3600
    created: set[str] = set()

    try:
        if need_panel_stages:
            _run_single_stage(
                aci, "weekly-prepare-aci", PREPARE_RESOURCES,
                {**base_env, "JOB_TYPE": "panel_prepare"},
                _secrets(["AZURE_STORAGE_CONNECTION_STRING"]), deadline, created,
            )
            _run_shards(aci, num_shards, base_env, _secrets(), deadline, created)

        if final_types:
            _run_single_stage(
                aci, "weekly-finalize-aci", FINALIZE_RESOURCES,
                {**base_env, "JOB_TYPE": ",".join(final_types)},
                _secrets(), deadline, created,
            )
        logger.info("Orchestration complete for %s.", week_label)
    finally:
        for name in sorted(created):
            try:
                aci.delete(name)
            except Exception:  # noqa: BLE001
                logger.exception("Could not delete %s during cleanup.", name)
