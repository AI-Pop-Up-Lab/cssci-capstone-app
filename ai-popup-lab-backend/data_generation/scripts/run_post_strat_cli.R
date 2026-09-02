args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 4) {
  stop(
    paste(
      "Usage:",
      "Rscript scripts/run_post_strat_cli.R <survey_csv> <frame_csv> <output_dir> <country> [n_sims] [compute_draws]"
    )
  )
}

get_script_path <- function() {
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)

  if (length(file_arg) == 0) {
    stop("Unable to determine script path for sourcing the module.")
  }

  normalizePath(sub("^--file=", "", file_arg[[1]]))
}

script_path <- get_script_path()
repo_root <- normalizePath(file.path(dirname(script_path), ".."))

survey_path <- args[[1]]
frame_path <- args[[2]]
output_dir <- args[[3]]
country <- args[[4]]
n_sims <- if (length(args) >= 5) as.integer(args[[5]]) else 250L

if (is.na(n_sims) || n_sims <= 0) {
  stop("n_sims must be a positive integer.")
}

# compute_draws = FALSE skips the simulation-draws phase entirely (and every
# output that depends on it: quartile/uncertainty tables, CD-level
# breakdowns) -- this is the memory-heavy part of the run. extended_frame,
# point_estimates, stage_diagnostics, and aggregate_counts are unaffected,
# since none of them depend on the draws. Defaults to TRUE (full output,
# original behavior) for standalone/manual invocations; the pipeline
# explicitly opts out via this arg when it only needs extended_frame.
compute_draws_arg <- if (length(args) >= 6) args[[6]] else "true"
compute_draws <- tolower(compute_draws_arg) %in% c("true", "1", "yes")

# Country-specific post-stratification module. The US module has its own
# stickbreaking/multinomial structure and district-level output tailored to
# US House races; every other country still uses the original shared
# module. Add more country-specific branches here as they're built out —
# both modules expose the same run_post_stratification()/
# write_post_strat_outputs() entry points, so this dispatch is the only
# thing that needs to change to add a new one.
module_file <- if (tolower(country) == "usa") {
  "post_strat_module_us.R"
} else {
  "post_strat_module_dk_se.R"
}

module_path <- file.path(dirname(script_path), module_file)
if (!file.exists(module_path)) {
  stop("Post-stratification module not found for country '", country, "': ", module_path)
}
source(module_path)

survey <- readr::read_csv(survey_path, show_col_types = FALSE)
frame <- readr::read_csv(frame_path, show_col_types = FALSE)

result <- run_post_stratification(
  survey = survey,
  frame = frame,
  config = list(
    verbose = TRUE,
    n_sims = n_sims,
    compute_draws = compute_draws
  )
)

write_post_strat_outputs(result, output_dir)

message("All CSV files written to: ", normalizePath(output_dir))
