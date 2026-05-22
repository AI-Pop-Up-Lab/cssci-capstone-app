# install_r_packages.R
# runs at docker image build via Dockerfile.worker.
# installs every R package script depends on
    
options(repos = c(CRAN = "https://cloud.r-project.org"))
install.packages(c(
  "survey",
  "dplyr",
  "readr"
  # add all your actual R package dependencies here
), dependencies = TRUE)