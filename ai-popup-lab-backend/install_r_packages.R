# install_r_packages.R
# runs at docker image build via Dockerfile.worker.
# installs every R package script depends on
    
options(repos = c(CRAN = "https://cloud.r-project.org"))

install.packages(c(
  "dplyr",
  "purrr",
  "readr",
  "tibble",
  "tidyr"
), dependencies = TRUE)

install.packages("remotes")

result <- tryCatch(
  remotes::install_github("mgoplerud/vglmer", upgrade = "never"),
  error = function(e) {
    message("ERROR installing vglmer: ", conditionMessage(e))
    quit(status = 1)
  }
)

message("R package installation complete")