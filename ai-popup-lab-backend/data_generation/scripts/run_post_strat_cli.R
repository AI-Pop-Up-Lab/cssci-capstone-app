args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 4) {
  stop(
    paste(
      "Usage:",
      "Rscript scripts/run_post_strat_cli.R <survey_csv> <frame_csv> <output_dir> <country> [n_sims] [compute_draws] [area_shares_csv]"
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

# NOTE: compute_draws no longer gates anything in the current
# post_strat_module_us.R -- run_post_stratification() always runs the full
# simulation-draws phase now (national_summary_95ci, share_draws,
# cd_party_draws/cd_party_ci, and every margin summary's CI all depend on
# it). The only remaining draws-related toggle on the R side is
# config$export_cell_draws (default FALSE), which controls only whether
# the raw per-cell draw matrix (mrp_cell_draws.csv) gets written, not
# whether draws are computed at all. This arg is still accepted and still
# threaded into config -- in case a country module reintroduces a real
# gate -- but for country == "usa" it currently has no effect on runtime.
compute_draws_arg <- if (length(args) >= 6) args[[6]] else "true"
compute_draws <- tolower(compute_draws_arg) %in% c("true", "1", "yes")

# Optional: area-level (state-level presidential + district-level
# congressional) vote shares. post_strat_module_us.R's
# run_post_stratification() takes this as a required positional argument
# (area_level_vote_shares, no default) -- omit only when sourcing a
# country module that doesn't take it.
area_shares_path <- if (length(args) >= 7 && nzchar(args[[7]])) args[[7]] else NULL

# Country-specific post-stratification module. The US module has its own
# stickbreaking/multinomial structure and district-level output tailored to
# US House races; every other country still uses the original shared
# module. Add more country-specific branches here as they're built out --
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

if (tolower(country) == "usa" && is.null(area_shares_path)) {
  stop(
    "country == 'usa' requires an area-level vote shares CSV (7th CLI arg) -- ",
    "post_strat_module_us.R's run_post_stratification() has no default for it."
  )
}

survey <- readr::read_csv(survey_path, show_col_types = FALSE)
frame <- readr::read_csv(frame_path, show_col_types = FALSE)

run_args <- list(
  survey = survey,
  frame = frame,
  config = list(
    verbose = TRUE,
    n_sims = n_sims,
    compute_draws = compute_draws
  )
)

if (!is.null(area_shares_path)) {
  run_args$area_level_vote_shares <- readr::read_csv(area_shares_path, show_col_types = FALSE)
}

result <- do.call(run_post_stratification, run_args)

write_post_strat_outputs(result, output_dir)

message("All CSV files written to: ", normalizePath(output_dir))
