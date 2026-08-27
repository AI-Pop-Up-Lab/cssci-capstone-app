args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 4) {
  stop(
    paste(
      "Usage:",
      "Rscript scripts/run_post_strat_cli.R <survey_csv> <frame_csv> <output_dir> <country> [n_sims]"
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
  "post_strat_module.R"
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
    n_sims = n_sims
  )
)

write_post_strat_outputs(result, output_dir)

message("All CSV files written to: ", normalizePath(output_dir))
