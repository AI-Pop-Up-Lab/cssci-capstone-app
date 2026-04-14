args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 3) {
  stop(
    paste(
      "Usage:",
      "Rscript scripts/run_post_strat_cli.R <survey_csv> <frame_csv> <output_dir> [n_sims]"
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

source(file.path(dirname(script_path), "post_strat_module.R"))

survey_path <- args[[1]]
frame_path <- args[[2]]
output_dir <- args[[3]]
n_sims <- if (length(args) >= 4) as.integer(args[[4]]) else 250L

if (is.na(n_sims) || n_sims <= 0) {
  stop("n_sims must be a positive integer.")
}

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
