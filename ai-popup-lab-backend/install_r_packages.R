# install_r_packages.R
# runs at docker image build via Dockerfile.worker.
# installs every R package script depends on
    
lib <- "/usr/local/lib/R/site-library"
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
message("Installing to: ", lib)

options(repos = c(CRAN = "https://cloud.r-project.org"))

install.packages(c(
  "dplyr", "purrr", "readr", "tibble", "tidyr", "remotes"
), dependencies = TRUE, lib = lib)

remotes::install_github("mgoplerud/vglmer", upgrade = "never", lib = lib)

message("Checking vglmer at: ", lib)
message("vglmer found: ", "vglmer" %in% rownames(installed.packages(lib.loc = lib)))
message("All libs: ", paste(.libPaths(), collapse = ", "))