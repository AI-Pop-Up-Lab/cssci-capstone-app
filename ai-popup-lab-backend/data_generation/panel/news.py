"""
Download GDELT 2.0 GKG records for a date range and source domain.

Example:
    from modules.news import download_weekly_news

    download_weekly_news("2025-04-28", "2025-05-04", domain=".nl")

Requirements:
    pip install requests pandas tqdm
"""

import io
import zipfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

MASTERLIST_URLS = [
    "http://data.gdeltproject.org/gdeltv2/masterfilelist.txt",
    "http://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt",
]
DEFAULT_MAX_WORKERS = 8

# ── GKG column names (27 columns, tab-separated, no header) ───────────────────
GKG_COLUMNS = [
    "GKGRECORDID", "DATE", "SourceCollectionIdentifier", "SourceCommonName",
    "DocumentIdentifier", "Counts", "V2Counts", "Themes", "V2Themes",
    "Locations", "V2Locations", "Persons", "V2Persons", "Organizations",
    "V2Organizations", "V2Tone", "Dates", "GCAM", "SharingImage",
    "RelatedImages", "SocialImageEmbeds", "SocialVideoEmbeds", "Quotations",
    "AllNames", "Amounts", "TranslationInfo", "Extras",
]

KEEP_COLUMNS = [
    "GKGRECORDID", "DATE", "SourceCommonName", "DocumentIdentifier",
    "V2Themes", "V2Locations", "V2Persons", "V2Organizations",
    "V2Tone", "Quotations", "SharingImage",
]


def _coerce_datetime(value: datetime | date | str) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(value)


def _normalize_domains(domain: str | list[str]) -> list[str]:
    raw_list = domain if isinstance(domain, list) else [domain]
    normalized = []
    for d in raw_list:
        d = d.strip().lower().lstrip(".")
        if d:
            normalized.append(d)
    if not normalized:
        raise ValueError("domain must contain at least one non-empty entry")
    return normalized


def _output_path(start: datetime, end: datetime, domain: str, output_dir: str | Path | None) -> Path:
    safe_domain = domain.lstrip(".").replace(".", "_")
    filename = (
        f"gdelt_gkg_{safe_domain}_sources_"
        f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
    )
    base_dir = Path(output_dir) if output_dir is not None else Path("data/gdelt")
    return base_dir / filename


# ── Step 1: Collect GKG file URLs for the date range ──────────────────────────
def get_gkg_urls(start: datetime, end: datetime, masterlist_urls: list[str] | None = None) -> list[str]:
    urls = []
    for master_url in (masterlist_urls or MASTERLIST_URLS):
        print(f"Fetching master list: {master_url}")
        resp = requests.get(master_url, timeout=60)
        resp.raise_for_status()
        end_inclusive = end + timedelta(days=1)
        for line in resp.text.splitlines():
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            url = parts[2]
            if not url.endswith(".gkg.csv.zip"):
                continue
            fname = url.split("/")[-1]
            try:
                file_dt = datetime.strptime(fname[:14], "%Y%m%d%H%M%S")
            except ValueError:
                continue
            if start <= file_dt < end_inclusive:
                urls.append(url)
    print(f"Found {len(urls)} total GKG files across both collections")
    return urls


# ── Step 2: Download one GKG zip, filter for .nl sources ──────────────────────
def download_and_filter(url: str, domains: list[str]) -> pd.DataFrame | None:
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(
                        f, sep="\t", header=None,
                        names=GKG_COLUMNS, dtype=str,
                        low_memory=False, on_bad_lines="skip",
                    )
            names = df["SourceCommonName"].fillna("").str.lower()
            mask = names.apply(
                lambda n: any(n == d or n.endswith(f".{d}") for d in domains)
            )
            filtered = df.loc[mask, [c for c in KEEP_COLUMNS if c in df.columns]]
            return filtered if not filtered.empty else None
        except Exception as e:
            if attempt == 2:
                print(f"  ✗ {url.split('/')[-1]} — {e}")
            time.sleep(2 ** attempt)
    return None


# ── Step 3: Parse V2Tone into named numeric columns ───────────────────────────
def parse_tone(df: pd.DataFrame) -> pd.DataFrame:
    if "V2Tone" not in df.columns:
        return df
    tone_parts = df["V2Tone"].str.split(",", expand=True)
    labels = ["tone", "tone_positive", "tone_negative",
              "tone_polarity", "tone_activity", "tone_selfref", "tone_wordcount"]
    for i, label in enumerate(labels):
        if i < tone_parts.shape[1]:
            df[label] = pd.to_numeric(tone_parts[i], errors="coerce")
    return df


def download_weekly_news(
    start_date, end_date,
    domain: str | list[str] = ".nl",
    output_file=None,
    max_workers=DEFAULT_MAX_WORKERS,
    masterlist_urls=None,
    save_csv=True,
) -> pd.DataFrame | None:
    start = _coerce_datetime(start_date)
    end = _coerce_datetime(end_date)
    normalized_domains = _normalize_domains(domain)
    output_path = Path(output_file) if output_file is not None else _output_path(
        start, end, normalized_domains[0], None  # filename just uses first domain as a label
    )

    t0 = time.time()
    urls = get_gkg_urls(start, end, masterlist_urls=masterlist_urls)
    if not urls:
        print("No GKG files found for the given date range.")
        return None

    results = []
    print(f"Downloading and filtering {len(urls)} files ({max_workers} threads)...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_and_filter, u, normalized_domains): u for u in urls}
        for future in tqdm(as_completed(futures), total=len(futures), unit="file"):
            df = future.result()
            if df is not None:
                results.append(df)

    if not results:
        print(f"No {normalized_domains} source records found.")
        return None

    combined = pd.concat(results, ignore_index=True)
    combined = combined.drop_duplicates(subset="DocumentIdentifier", keep="first")
    combined = combined.sort_values("DATE").reset_index(drop=True)
    combined = parse_tone(combined)

    if save_csv:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(output_path, index=False)

    elapsed = time.time() - t0
    print(f"\n✓ Done in {elapsed:.1f}s")
    print(f"  Unique articles  : {len(combined):,}")
    print(f"  Unique sources   : {combined['SourceCommonName'].nunique():,}")
    print(f"\nTop 10 {normalized_domains} sources:")
    print(combined["SourceCommonName"].value_counts().head(10).to_string())

    return combined




# GET ARTICLE TEXT, TITLE AND AUTHORS 
import newspaper

def fetch_article(url: str) -> dict[str, str | None]:
    try:
        article = newspaper.Article(url)
        article.download()
        article.parse()
        return {
            "title": article.title,
            "authors": ", ".join(article.authors) if article.authors else None,
            "text": article.text,
        }
    except Exception as e:
        print(f"  ✗ Failed to fetch {url} — {e}")
        return {"title": None, "authors": None, "text": None}


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    # download_weekly_news("2026-05-04", "2026-05-10", domain=".se")
    print(fetch_article("https://www.dn.se/direkt/2026-05-07/barn-fran-13-ar-kan-overvakas-elektroniskt/"))


if __name__ == "__main__":
    main()



