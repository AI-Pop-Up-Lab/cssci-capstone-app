# install_r_packages.R
# runs at docker image build via Dockerfile.worker.
# installs every R package script depends on
    
options(repos = c(CRAN = "https://cloud.r-project.org"))
install.packages(c(
  "survey",
  "dplyr",
  "purrr",
  "readr",
  "tibble",
  "tidyr"
), dependencies = TRUE)

install.packages("remotes", repos = "https://cloud.r-project.org")
remotes::install_github("mgoplerud/vglmer")