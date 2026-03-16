library(tidyverse)
library(vglmer)
library(purrr)

frame <- read_csv("data/FOLK1D_HFUDD11_combined.csv")
dnes  <- read_csv("data/DNES_2022_recoded.csv")

# --- Stratification frame overview ---
cat("=== Stratification Frame (FOLK1D) ===\n")
cat("Rows:", nrow(frame), "| Cols:", ncol(frame), "\n")
glimpse(frame)



# DNES overview
cat("=== DNES 2022 Survey ===\n")
cat("Rows:", nrow(dnes), "| Cols:", ncol(dnes), "\n")
glimpse(dnes)




# =============================================================
# HARMONISATION
# =============================================================

# 1. Drop "Other" gender — no matching frame cell
dnes <- dnes |> filter(gender != "Other")

# 2. Fix duplicate H30 education label in DNES


# 4b. Collapse H2030 (frame-only) into the nearest DNES education level


# =============================================================

# --- Clean up the index columns ---
frame <- frame |> select(-`...1`)
dnes  <- dnes  |> select(-`Unnamed: 0`)

# ===== FRAME DESCRIPTIVES =====
cat("=== Frame: key strata dimensions ===\n")

cat("\nMunicipalities:", n_distinct(frame$municipality), "\n")
cat("Age groups:", n_distinct(frame$age_group), "\n")
cat("Education categories:", n_distinct(frame$education), "\n")
cat("Gender categories:", paste(unique(frame$gender), collapse = ", "), "\n")

cat("\n-- Total population count --\n")
frame |>
  distinct(municipality, gender, age_group, N) |>
  summarise(total_pop = sum(N)) |>
  pull(total_pop) |>
  formatC(big.mark = ",") |>
  cat()

cat("\n\n-- N distribution summary (cells in frame) --\n")
summary(frame$N)


# ===== DNES DESCRIPTIVES =====
cat("=== DNES: missingness in key MRP variables ===\n")
dnes |>
  select(vote_in_2022, gender, age_group, education_level, municipality) |>
  summarise(across(everything(), ~ mean(is.na(.)) * 100)) |>
  pivot_longer(everything(), names_to = "variable", values_to = "pct_missing") |>
  mutate(pct_missing = round(pct_missing, 1))





library(dplyr)
library(tidyr)
library(purrr)
library(forcats)
library(vglmer)
library(tibble)
library(readr)

# ============================================================
# 0) SETTINGS
# ============================================================

eps <- 1e-8
verbose <- TRUE
n_sims <- 250
output_dir <- "mrp_outputs"

msg <- function(...) {
  if (isTRUE(verbose)) message(...)
}

if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

# ============================================================
# 1) PARTY RECODING
#    Match the Python collapsing logic exactly
# ============================================================

other_left <- c(
  "Ø: Enhedslisten",
  "Å: Alternativet",
  "B: Det Radikale Venstre"
)

other_right <- c(
  "C: Det Konservative Folkeparti",
  "D: Nye Borgerlige",
  "O: Dansk Folkeparti"
)

other <- c(
  "Independent candidate",
  "Another party",
  "Voted blank"
)

recode_party <- function(party) {
  case_when(
    party %in% other_left  ~ "Other - Left",
    party %in% other_right ~ "Other - Right",
    party %in% other       ~ "Other",
    TRUE                   ~ party
  )
}

# ============================================================
# 2) LOAD 2022 MUNICIPAL PARTY RESULTS
#    vote_pct comes only from here
# ============================================================

election_results <- read_csv(
  "data/denmark_election_results_with_turnout.csv",
  show_col_types = FALSE
) %>%
  filter(year == 2022) %>%
  mutate(
    party = recode_party(as.character(party)),
    municipality = as.character(municipality),
    pop_pct = as.numeric(pop_pct)
  ) %>%
  filter(
    !is.na(party),
    !is.na(municipality),
    !is.na(pop_pct)
  ) %>%
  group_by(municipality, party) %>%
  summarise(
    vote_pct = sum(pop_pct, na.rm = TRUE),
    .groups = "drop"
  )

if (nrow(election_results) == 0) {
  stop("No usable 2022 election results found in denmark_election_results_with_turnout.csv.")
}

# ============================================================
# 3) PREP SURVEY DATA
#    No permanent vote_pct column in survey; it gets joined per stage
# ============================================================

required_vars <- c(
  "vote_in_2022",
  "gender",
  "age_group",
  "education_level",
  "municipality"
)

dnes_model <- dnes %>%
  mutate(
    vote_in_2022    = recode_party(as.character(vote_in_2022)),
    gender          = as.character(gender),
    age_group       = as.character(age_group),
    education_level = as.character(education_level),
    municipality    = as.character(municipality)
  ) %>%
  filter(
    if_all(all_of(required_vars), ~ !is.na(.x) & .x != "")
  ) %>%
  mutate(
    gender          = factor(gender),
    age_group       = factor(age_group),
    education_level = factor(education_level),
    municipality    = factor(municipality)
  )

if (nrow(dnes_model) == 0) {
  stop("No complete cases remain in `dnes` after filtering model variables.")
}

# ============================================================
# 4) DEFINE PARTY ORDER
# ============================================================

party_order <- dnes_model %>%
  count(vote_in_2022, sort = TRUE) %>%
  pull(vote_in_2022)

if ("Did not vote" %in% party_order) {
  parties <- c("Did not vote", setdiff(party_order, "Did not vote"))
} else {
  parties <- party_order
}

K <- length(parties)

if (K < 2) {
  stop("Need at least two outcome categories in `vote_in_2022` after filtering.")
}

dnes_model <- dnes_model %>%
  mutate(vote_in_2022 = factor(vote_in_2022, levels = parties))

# ============================================================
# 5) PREP POSTSTRATIFICATION FRAME
#    Still no permanent vote_pct here
# ============================================================

if (!("education" %in% names(frame)) && !("education_level" %in% names(frame))) {
  stop("`frame` must contain either `education` or `education_level`.")
}

frame_pred <- frame %>%
  rename(education_level = any_of("education")) %>%
  mutate(
    gender          = as.character(gender),
    age_group       = as.character(age_group),
    education_level = as.character(education_level),
    municipality    = as.character(municipality)
  ) %>%
  filter(
    !is.na(gender), !is.na(age_group),
    !is.na(education_level), !is.na(municipality),
    !is.na(N), N > 0
  )

if (nrow(frame_pred) == 0) {
  stop("No usable rows remain in `frame` after filtering.")
}

survey_levels <- list(
  gender          = levels(dnes_model$gender),
  age_group       = levels(dnes_model$age_group),
  education_level = levels(dnes_model$education_level),
  municipality    = levels(dnes_model$municipality)
)

frame_unseen <- list(
  gender          = setdiff(unique(frame_pred$gender), survey_levels$gender),
  age_group       = setdiff(unique(frame_pred$age_group), survey_levels$age_group),
  education_level = setdiff(unique(frame_pred$education_level), survey_levels$education_level),
  municipality    = setdiff(unique(frame_pred$municipality), survey_levels$municipality)
)

if (length(frame_unseen$gender) > 0) {
  stop("Unseen gender levels in frame: ", paste(frame_unseen$gender, collapse = ", "))
}
if (length(frame_unseen$age_group) > 0) {
  stop("Unseen age_group levels in frame: ", paste(frame_unseen$age_group, collapse = ", "))
}
if (length(frame_unseen$education_level) > 0) {
  stop("Unseen education_level levels in frame: ", paste(frame_unseen$education_level, collapse = ", "))
}

if (length(frame_unseen$municipality) > 0) {
  msg(
    "There are ", length(frame_unseen$municipality),
    " municipalities in the frame not seen in the survey. ",
    "These rows will be excluded from municipality-level summaries ",
    "because municipality becomes NA after factor alignment."
  )
}

frame_pred <- frame_pred %>%
  mutate(
    gender          = factor(gender, levels = survey_levels$gender),
    age_group       = factor(age_group, levels = survey_levels$age_group),
    education_level = factor(education_level, levels = survey_levels$education_level),
    municipality    = factor(municipality, levels = survey_levels$municipality)
  )

# ============================================================
# 6) HELPER: ADD vote_pct ONLY FOR THE CURRENT STAGE PARTY
# ============================================================

add_interactions <- function(dat,
                             age_edu_levels = NULL,
                             age_gender_levels = NULL,
                             gender_edu_levels = NULL) {
  age_edu_raw <- interaction(dat$age_group, dat$education_level, drop = TRUE, sep = "___")
  age_gender_raw <- interaction(dat$age_group, dat$gender, drop = TRUE, sep = "___")
  gender_edu_raw <- interaction(dat$gender, dat$education_level, drop = TRUE, sep = "___")

  dat$age_edu <- if (is.null(age_edu_levels)) {
    factor(age_edu_raw)
  } else {
    factor(as.character(age_edu_raw), levels = age_edu_levels)
  }

  dat$age_gender <- if (is.null(age_gender_levels)) {
    factor(age_gender_raw)
  } else {
    factor(as.character(age_gender_raw), levels = age_gender_levels)
  }

  dat$gender_edu <- if (is.null(gender_edu_levels)) {
    factor(gender_edu_raw)
  } else {
    factor(as.character(gender_edu_raw), levels = gender_edu_levels)
  }

  dat
}

make_stage_data <- function(data, party_name, vote_lookup,
                            age_edu_levels = NULL,
                            age_gender_levels = NULL,
                            gender_edu_levels = NULL) {
  
  lookup_sub <- vote_lookup %>%
    filter(party == party_name) %>%
    transmute(
      municipality_chr = as.character(municipality),
      vote_pct_stage = as.numeric(vote_pct)
    )

  joined <- data %>%
    select(-any_of(c(
      "vote_pct", "vote_pct_scaled", "vote_pct_stage",
      "age_edu", "age_gender", "gender_edu"
    ))) %>%
    mutate(municipality_chr = as.character(municipality)) %>%
    left_join(lookup_sub, by = "municipality_chr") %>%
    mutate(
      vote_pct = coalesce(vote_pct_stage, 0),
      vote_pct_scaled = as.numeric(scale(vote_pct)),
      vote_pct_scaled = if_else(is.na(vote_pct_scaled), 0, vote_pct_scaled)
    ) %>%
    select(-municipality_chr, -vote_pct_stage)

  age_edu_raw <- interaction(joined$age_group, joined$education_level, drop = TRUE)
  age_gender_raw <- interaction(joined$age_group, joined$gender, drop = TRUE)
  gender_edu_raw <- interaction(joined$gender, joined$education_level, drop = TRUE)

  joined$age_edu <- if (is.null(age_edu_levels)) {
    factor(age_edu_raw)
  } else {
    factor(age_edu_raw, levels = age_edu_levels)
  }

  joined$age_gender <- if (is.null(age_gender_levels)) {
    factor(age_gender_raw)
  } else {
    factor(age_gender_raw, levels = age_gender_levels)
  }

  joined$gender_edu <- if (is.null(gender_edu_levels)) {
    factor(gender_edu_raw)
  } else {
    factor(gender_edu_raw, levels = gender_edu_levels)
  }

  joined <- add_interactions(
  joined,
  age_edu_levels = age_edu_levels,
  age_gender_levels = age_gender_levels,
  gender_edu_levels = gender_edu_levels
)

  joined
}
# ============================================================
# 7) STICK-BREAKING FIT FUNCTION
# ============================================================

fit_one_stage <- function(dat, party_name, min_n = 80, min_events = 15) {
  d <- dat %>%
    mutate(
      y = as.integer(vote_in_2022 == party_name),
      gender          = droplevels(gender),
      age_group       = droplevels(age_group),
      education_level = droplevels(education_level),
      municipality    = droplevels(municipality),
      vote_in_2022    = droplevels(vote_in_2022)
    )
  
  d <- add_interactions(d)
  
  # d <- dat %>%
  # mutate(
  #   y = as.integer(vote_in_2022 == party_name),
  #   gender          = droplevels(gender),
  #   age_group       = droplevels(age_group),
  #   education_level = droplevels(education_level),
  #   municipality    = droplevels(municipality),
  #   vote_in_2022    = droplevels(vote_in_2022)
  # ) %>%
  # mutate(
  #   age_edu    = factor(interaction(age_group, education_level, drop = TRUE)),
  #   age_gender = factor(interaction(age_group, gender, drop = TRUE)),
  #   gender_edu = factor(interaction(gender, education_level, drop = TRUE))
  # )

  n_total <- nrow(d)
  n_event <- sum(d$y, na.rm = TRUE)
  use_interactions <- n_total >= 300

  fallback_prob <- if (n_total > 0) n_event / n_total else 0
  fallback_prob <- pmin(pmax(fallback_prob, eps), 1 - eps)

  if (n_total < min_n || n_event < min_events || (n_total - n_event) < min_events) {
    return(list(
      fit = NULL,
      fallback_prob = fallback_prob,
      n_total = n_total,
      n_event = n_event,
      status = "fallback_sparse"
    ))
  }

formula_full <- if (use_interactions) {
  y ~ v_s(vote_pct) +
    (1 | municipality) +
    (1 | gender) +
    (1 | age_group) +
    (1 | education_level) +
    (1 | age_edu) +
    (1 | age_gender) +
    (1 | gender_edu)
} else {
  y ~ v_s(vote_pct) +
    (1 | municipality) +
    (1 | gender) +
    (1 | age_group) +
    (1 | education_level)
}

fit_full <- tryCatch(
  vglmer(
    formula_full,
    data = d,
    family = "binomial",
    control = vglmer_control(iterations = 15000)
  ),
  error = function(e) {
    msg("fit_full failed for ", party_name)
    msg("  error: ", conditionMessage(e))
    NULL
  }
)

  if (!is.null(fit_full)) {
    return(list(
      fit = fit_full,
      fallback_prob = fallback_prob,
      n_total = n_total,
      n_event = n_event,
      status = "fit_ok_full",
      age_edu_levels = levels(d$age_edu),
      age_gender_levels = levels(d$age_gender),
      gender_edu_levels = levels(d$gender_edu)
    ))
  }

  fit_simple <- tryCatch(
  vglmer(
    y ~ gender + age_group + education_level + vote_pct,
    data = d,
    family = "binomial",
    control = vglmer_control(iterations = 5000)
  ),
  error = function(e) {
    msg("fit_simple failed for ", party_name, ": ", conditionMessage(e))
    NULL
  }
)

  if (!is.null(fit_simple)) {
    return(list(
      fit = fit_simple,
      fallback_prob = fallback_prob,
      n_total = n_total,
      n_event = n_event,
      status = "fit_ok_simple"
    ))
  }

  list(
    fit = NULL,
    fallback_prob = fallback_prob,
    n_total = n_total,
    n_event = n_event,
    status = "fallback_error"
  )
}

# ============================================================
# 8) FIT ALL STICK-BREAKING STAGES
#    vote_pct is joined only for the current stage party
# ============================================================

sb_fits <- vector("list", K - 1)
names(sb_fits) <- parties[seq_len(K - 1)]

remaining_parties <- parties

for (k in seq_len(K - 1)) {
  current_party <- remaining_parties[1]

  d_k_base <- dnes_model %>%
    filter(vote_in_2022 %in% remaining_parties) %>%
    mutate(vote_in_2022 = droplevels(vote_in_2022)) %>%
    droplevels()

  d_k <- make_stage_data(d_k_base, current_party, election_results)

  stage_fit <- fit_one_stage(d_k, current_party)
  sb_fits[[k]] <- stage_fit

  msg(
    "Stage ", k, "/", K - 1, " [", current_party, "] : ",
    stage_fit$status, " | n=", stage_fit$n_total,
    " | events=", stage_fit$n_event,
    " | fallback=", round(stage_fit$fallback_prob, 6)
  )

  remaining_parties <- remaining_parties[-1]
}

# ============================================================
# 9) PREDICTION HELPERS
# ============================================================

predict_stage_point <- function(stage_obj, newdata) {
  if (is.null(stage_obj$fit)) {
    return(rep(stage_obj$fallback_prob, nrow(newdata)))
  }

  eta <- tryCatch(
    predict_MAVB(
      stage_obj$fit,
      newdata = newdata,
      samples = 1,
      summary = TRUE,
      allow_missing_levels = TRUE
    ),
    error = function(e) {
      msg("Point prediction failed; reverting to fallback: ", conditionMessage(e))
      return(e)
    }
  )

  if (inherits(eta, "error")) {
    return(rep(stage_obj$fallback_prob, nrow(newdata)))
  }

  # DEBUG: inspect returned object
  msg("predict_MAVB point return class: ", paste(class(eta), collapse = ", "))
  msg("predict_MAVB point return names: ", paste(names(eta), collapse = ", "))

  # Try to extract the mean/eta component if a list is returned
  if (is.list(eta)) {
    if ("mean" %in% names(eta)) {
      eta <- eta$mean
    } else if ("fit" %in% names(eta)) {
      eta <- eta$fit
    } else if ("pred" %in% names(eta)) {
      eta <- eta$pred
    } else if (length(eta) == 1) {
      eta <- eta[[1]]
    } else {
      msg("Unknown list structure from predict_MAVB(); using fallback")
      return(rep(stage_obj$fallback_prob, nrow(newdata)))
    }
  }

  eta <- as.numeric(eta)
  p <- plogis(eta)
  pmin(pmax(p, eps), 1 - eps)
}

predict_stage_draws <- function(stage_obj, newdata, n_sims = 250) {
  if (is.null(stage_obj$fit)) {
    return(matrix(stage_obj$fallback_prob, nrow = nrow(newdata), ncol = n_sims))
  }

  eta_draws <- tryCatch(
    predict_MAVB(
      stage_obj$fit,
      newdata = newdata,
      samples = n_sims,
      summary = FALSE,
      allow_missing_levels = TRUE
    ),
    error = function(e) e
  )

  if (inherits(eta_draws, "error")) {
    msg("Simulation prediction failed; reverting to fallback: ", conditionMessage(eta_draws))
    return(matrix(stage_obj$fallback_prob, nrow = nrow(newdata), ncol = n_sims))
  }

  eta_draws <- as.matrix(eta_draws)

  if (nrow(eta_draws) == n_sims && ncol(eta_draws) == nrow(newdata)) {
    eta_draws <- t(eta_draws)
  } else if (nrow(eta_draws) == nrow(newdata) && ncol(eta_draws) == n_sims) {
    # already correct
  } else {
    stop(
      "Unexpected dimensions from predict_MAVB(): got ",
      nrow(eta_draws), " x ", ncol(eta_draws),
      ", expected either ", nrow(newdata), " x ", n_sims,
      " or ", n_sims, " x ", nrow(newdata), "."
    )
  }

  p_draws <- plogis(eta_draws)
  pmin(pmax(p_draws, eps), 1 - eps)
}

# ============================================================
# 10) POINT ESTIMATES
#    vote_pct is joined only per stage
# ============================================================

pi_mat <- matrix(NA_real_, nrow = nrow(frame_pred), ncol = K - 1)
colnames(pi_mat) <- parties[seq_len(K - 1)]

for (k in seq_len(K - 1)) {
  stage_newdata <- make_stage_data(
  frame_pred,
  parties[k],
  election_results,
  age_edu_levels = sb_fits[[k]]$age_edu_levels,
  age_gender_levels = sb_fits[[k]]$age_gender_levels,
  gender_edu_levels = sb_fits[[k]]$gender_edu_levels
)
  pi_mat[, k] <- predict_stage_point(sb_fits[[k]], stage_newdata)
}

prob_mat <- matrix(0, nrow = nrow(frame_pred), ncol = K)
colnames(prob_mat) <- parties

remaining_mass <- rep(1, nrow(frame_pred))

for (k in seq_len(K - 1)) {
  prob_mat[, k] <- remaining_mass * pi_mat[, k]
  remaining_mass <- remaining_mass * (1 - pi_mat[, k])
}

prob_mat[, K] <- remaining_mass

prob_mat[prob_mat < 0] <- 0
row_sums <- rowSums(prob_mat)

bad_rows <- which(!is.finite(row_sums) | row_sums <= 0)
if (length(bad_rows) > 0) {
  warning(length(bad_rows), " rows had invalid probability sums; replacing with uniform distribution.")
  prob_mat[bad_rows, ] <- 1 / K
  row_sums[bad_rows] <- 1
}

prob_mat <- prob_mat / row_sums
stopifnot(all(abs(rowSums(prob_mat) - 1) < 1e-6))

# ============================================================
# 11) NATIONAL POINT ESTIMATES
# ============================================================

mrp_estimates <- as_tibble(prob_mat) %>%
  mutate(weight = frame_pred$N) %>%
  summarise(across(-weight, ~ weighted.mean(.x, w = weight, na.rm = TRUE))) %>%
  pivot_longer(
    everything(),
    names_to = "party",
    values_to = "point_estimate"
  ) %>%
  arrange(desc(point_estimate))

print(mrp_estimates)

# ============================================================
# 12) DRAWS FOR UNCERTAINTY
#    vote_pct is joined only per stage
# ============================================================

pi_draws <- vector("list", K - 1)

for (k in seq_len(K - 1)) {
  msg("Simulation draws for stage ", k, "/", K - 1, " [", parties[k], "]")
  stage_newdata <- make_stage_data(
  frame_pred,
  parties[k],
  election_results,
  age_edu_levels = sb_fits[[k]]$age_edu_levels,
  age_gender_levels = sb_fits[[k]]$age_gender_levels,
  gender_edu_levels = sb_fits[[k]]$gender_edu_levels
)
  pi_draws[[k]] <- predict_stage_draws(sb_fits[[k]], stage_newdata, n_sims = n_sims)
}

# ============================================================
# 13) NATIONAL PARTY SHARES FOR EACH DRAW
# ============================================================

share_draws <- matrix(NA_real_, nrow = n_sims, ncol = K)
colnames(share_draws) <- parties

weights <- frame_pred$N

for (s in seq_len(n_sims)) {
  remaining_mass_s <- rep(1, nrow(frame_pred))
  prob_mat_s <- matrix(0, nrow = nrow(frame_pred), ncol = K)
  colnames(prob_mat_s) <- parties

  for (k in seq_len(K - 1)) {
    pks <- pi_draws[[k]][, s]
    prob_mat_s[, k] <- remaining_mass_s * pks
    remaining_mass_s <- remaining_mass_s * (1 - pks)
  }

  prob_mat_s[, K] <- remaining_mass_s

  prob_mat_s[prob_mat_s < 0] <- 0
  rs <- rowSums(prob_mat_s)

  bad_rows_s <- which(!is.finite(rs) | rs <= 0)
  if (length(bad_rows_s) > 0) {
    prob_mat_s[bad_rows_s, ] <- 1 / K
    rs[bad_rows_s] <- 1
  }

  prob_mat_s <- prob_mat_s / rs

  share_draws[s, ] <- apply(
    prob_mat_s,
    2,
    weighted.mean,
    w = weights,
    na.rm = TRUE
  )
}

# ============================================================
# 14) NATIONAL QUARTILE TABLE
# ============================================================

quartile_table <- tibble(
  party = parties,
  lower_quartile = apply(share_draws, 2, quantile, probs = 0.25, na.rm = TRUE),
  median = apply(share_draws, 2, quantile, probs = 0.50, na.rm = TRUE),
  upper_quartile = apply(share_draws, 2, quantile, probs = 0.75, na.rm = TRUE)
) %>%
  left_join(mrp_estimates, by = "party") %>%
  select(party, point_estimate, lower_quartile, median, upper_quartile) %>%
  arrange(desc(point_estimate))

print(quartile_table)

# ============================================================
# 15) EXTENDED CELL-PARTY FRAME
#    vote_pct is not stored globally here either
# ============================================================

extended_frame <- as_tibble(prob_mat) %>%
  mutate(cell_id = seq_len(nrow(frame_pred))) %>%
  pivot_longer(
    cols = -cell_id,
    names_to = "party",
    values_to = "prob"
  ) %>%
  left_join(
    frame_pred %>% mutate(cell_id = seq_len(n())),
    by = "cell_id"
  ) %>%
  mutate(
    expected_N = N * prob
  ) %>%
  select(
    cell_id, age_group, gender, municipality, education_level,
    N, party, prob, expected_N
  )

print(extended_frame)

# ============================================================
# 16) DIAGNOSTICS
# ============================================================

stage_diagnostics <- tibble(
  stage = seq_len(K - 1),
  party = parties[seq_len(K - 1)],
  status = map_chr(sb_fits, "status"),
  n_total = map_dbl(sb_fits, "n_total"),
  n_event = map_dbl(sb_fits, "n_event"),
  fallback_prob = map_dbl(sb_fits, "fallback_prob")
)

print(stage_diagnostics)

aggregate_counts <- extended_frame %>%
  group_by(party) %>%
  summarise(
    expected_total = sum(expected_N, na.rm = TRUE),
    expected_share = sum(expected_N, na.rm = TRUE) / sum(N[!duplicated(cell_id)]),
    .groups = "drop"
  ) %>%
  arrange(desc(expected_share))

print(aggregate_counts)

# ============================================================
# 17) MUNICIPALITY x PARTY POINT ESTIMATES
# ============================================================

valid_rows <- !is.na(frame_pred$municipality)

municipality_party_point <- as_tibble(prob_mat[valid_rows, , drop = FALSE]) %>%
  mutate(
    municipality = as.character(frame_pred$municipality[valid_rows]),
    N = frame_pred$N[valid_rows]
  ) %>%
  pivot_longer(
    cols = all_of(parties),
    names_to = "party",
    values_to = "prob"
  ) %>%
  mutate(expected_N = N * prob) %>%
  group_by(municipality, party) %>%
  summarise(
    expected_N = sum(expected_N, na.rm = TRUE),
    total_N = sum(N, na.rm = TRUE),
    point_estimate = expected_N / total_N,
    .groups = "drop"
  )

print(municipality_party_point)

# ============================================================
# 18) MUNICIPALITY x PARTY DRAWS
# ============================================================

municipality_valid <- as.character(frame_pred$municipality[valid_rows])
weights_valid <- frame_pred$N[valid_rows]

municipality_party_draws_list <- vector("list", n_sims)

for (s in seq_len(n_sims)) {
  remaining_mass_s <- rep(1, nrow(frame_pred))
  prob_mat_s <- matrix(0, nrow = nrow(frame_pred), ncol = K)
  colnames(prob_mat_s) <- parties

  for (k in seq_len(K - 1)) {
    pks <- pi_draws[[k]][, s]
    prob_mat_s[, k] <- remaining_mass_s * pks
    remaining_mass_s <- remaining_mass_s * (1 - pks)
  }

  prob_mat_s[, K] <- remaining_mass_s

  prob_mat_s[prob_mat_s < 0] <- 0
  rs <- rowSums(prob_mat_s)

  bad_rows_s <- which(!is.finite(rs) | rs <= 0)
  if (length(bad_rows_s) > 0) {
    prob_mat_s[bad_rows_s, ] <- 1 / K
    rs[bad_rows_s] <- 1
  }

  prob_mat_s <- prob_mat_s / rs

  municipality_party_draws_list[[s]] <- as_tibble(prob_mat_s[valid_rows, , drop = FALSE]) %>%
    mutate(
      municipality = municipality_valid,
      N = weights_valid,
      draw = s
    ) %>%
    pivot_longer(
      cols = all_of(parties),
      names_to = "party",
      values_to = "prob"
    ) %>%
    mutate(expected_N = N * prob) %>%
    group_by(draw, municipality, party) %>%
    summarise(
      expected_N = sum(expected_N, na.rm = TRUE),
      total_N = sum(N, na.rm = TRUE),
      share = expected_N / total_N,
      .groups = "drop"
    )
}

municipality_party_draws <- bind_rows(municipality_party_draws_list)

print(municipality_party_draws)

# ============================================================
# 19) MUNICIPALITY x PARTY QUARTILES
# ============================================================

municipality_party_quartiles <- municipality_party_draws %>%
  group_by(municipality, party) %>%
  summarise(
    lower_quartile = quantile(share, probs = 0.25, na.rm = TRUE),
    median = quantile(share, probs = 0.50, na.rm = TRUE),
    upper_quartile = quantile(share, probs = 0.75, na.rm = TRUE),
    sd_draws = sd(share, na.rm = TRUE),
    n_distinct_draws = n_distinct(share),
    .groups = "drop"
  ) %>%
  left_join(municipality_party_point, by = c("municipality", "party")) %>%
  select(
    municipality,
    party,
    point_estimate,
    lower_quartile,
    median,
    upper_quartile,
    sd_draws,
    n_distinct_draws
  ) %>%
  arrange(municipality, desc(point_estimate))

print(municipality_party_quartiles)

# ============================================================
# 20) OPTIONAL LONG NATIONAL DRAWS
# ============================================================

share_draws_long <- as_tibble(share_draws) %>%
  mutate(draw = seq_len(n())) %>%
  pivot_longer(
    cols = -draw,
    names_to = "party",
    values_to = "share"
  )

print(share_draws_long)

# ============================================================
# 21) WRITE EVERYTHING TO CSV
# ============================================================

write_csv(
  mrp_estimates,
  file.path(output_dir, "mrp_point_estimates.csv")
)

write_csv(
  quartile_table,
  file.path(output_dir, "mrp_quartile_table.csv")
)

write_csv(
  extended_frame,
  file.path(output_dir, "mrp_extended_frame.csv")
)

write_csv(
  stage_diagnostics,
  file.path(output_dir, "mrp_stage_diagnostics.csv")
)

write_csv(
  aggregate_counts,
  file.path(output_dir, "mrp_aggregate_counts.csv")
)

write_csv(
  as_tibble(share_draws),
  file.path(output_dir, "mrp_share_draws_250.csv")
)

write_csv(
  share_draws_long,
  file.path(output_dir, "mrp_share_draws_250_long.csv")
)

write_csv(
  as_tibble(prob_mat),
  file.path(output_dir, "mrp_cell_party_probabilities.csv")
)

write_csv(
  as_tibble(pi_mat),
  file.path(output_dir, "mrp_stickbreaking_conditional_probs.csv")
)

write_csv(
  municipality_party_point,
  file.path(output_dir, "mrp_municipality_party_point_estimates.csv")
)

write_csv(
  municipality_party_draws,
  file.path(output_dir, "mrp_municipality_party_draws_250_long.csv")
)

write_csv(
  municipality_party_quartiles,
  file.path(output_dir, "mrp_municipality_party_quartiles.csv")
)

msg("All CSV files written to: ", normalizePath(output_dir))