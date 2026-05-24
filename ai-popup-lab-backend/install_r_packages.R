# install_r_packages.R
# runs at docker image build via Dockerfile.worker.
# installs every R package script depends on
    
options(repos = c(CRAN = "https://cloud.r-project.org"))

lib <- "/usr/local/lib/R/site-library"
dir.create(lib, recursive = TRUE, showWarnings = FALSE)

install.packages(c(
  "dplyr",
  "purrr", 
  "readr",
  "tibble",
  "tidyr"
), dependencies = TRUE, lib = lib)

install.packages("remotes", lib = lib)
remotes::install_github("mgoplerud/vglmer", upgrade = "never", lib = lib)

message("Done. Installed: ", paste(rownames(installed.packages(lib.loc = lib)), collapse = ", "))