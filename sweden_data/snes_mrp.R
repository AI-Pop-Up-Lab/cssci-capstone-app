library(tidyverse)
library(vglmer)
library(purrr)
library(tibble)
library(readr)

eps        <- 1e-8
verbose    <- TRUE
n_sims     <- 250
output_dir <- "mrp_outputs"

msg <- function(...) if (isTRUE(verbose)) message(...)
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

# =============================================================
# 1) LOAD DATA
# =============================================================

frame <- read_csv("sweden_strat_frame.csv", show_col_types = FALSE)
snes  <- read_csv("SNES22_recoded.csv",     show_col_types = FALSE)

election_results <- read_csv(
  "sweden_election_results_2022_municipality.csv",
  show_col_types = FALSE
)

# =============================================================
# 2) PARTY RECODING
# =============================================================

riksdag_parties <- c(
  "Left Party (V)", "Social Democrats (S)", "Centre Party (C)",
  "The Liberals (L)", "Moderate Party (M)", "Christian Democrats (KD)",
  "Green Party (MP)", "Sweden Democrats (SD)", "Did not vote", "Other party" 
)

# =============================================================
# 3) PREP SURVEY
# =============================================================

snes <- snes %>%
  mutate(vote_in_2022 = if_else(
    turnout_2022 == "Did not vote" & is.na(vote_in_2022),
    "Did not vote",
    vote_in_2022
  ))

edu_simple <- c(
  "Primary school, shorter than 9 years"     = "edu1",
  "Primary school, 9/10 years"               = "edu2",
  "Upper secondary school"                   = "edu3",
  "Tertiary education, shorter than 2 years" = "edu4",
  "Tertiary education, 2 years or longer"    = "edu5",
  "Postgraduate education"                   = "edu6",
  # Frame labels
  "Primary <9yr"   = "edu1",
  "Primary 9-10yr" = "edu2",
  "Upper secondary" = "edu3",
  "Tertiary <2yr"  = "edu4",
  "Tertiary 2yr+"  = "edu5",
  "Postgraduate"   = "edu6"
)

age_simple <- c(
  "18-22"  = "age1", "23-30" = "age2", "31-40" = "age3",
  "41-50"  = "age4", "51-60" = "age5", "61-70" = "age6",
  "71-104" = "age7"
)

gender_simple <- c("Women" = "F", "Men" = "M", "Female" = "F", "Male" = "M")

snes_model <- snes %>%
  mutate(
    vote_in_2022      = recode_party(as.character(vote_in_2022)),
    gender            = recode(as.character(gender),    !!!gender_simple),
    age_group         = recode(as.character(age_group), !!!age_simple),
    education         = recode(as.character(education), !!!edu_simple),
    municipality_code = as.character(municipality_code)
  ) %>%
  filter(if_all(
    c("vote_in_2022", "gender", "age_group", "education", "municipality_code"),
    ~ !is.na(.x) & .x != ""
  )) %>%
  mutate(
    gender            = factor(gender),
    age_group         = factor(age_group),
    education         = factor(education),
    municipality_code = factor(municipality_code)
  )

# =============================================================
# 4) PARTY ORDER
# =============================================================

party_order <- snes_model %>% count(vote_in_2022, sort = TRUE) %>% pull(vote_in_2022)
parties     <- c("Did not vote", setdiff(party_order, "Did not vote"))
K           <- length(parties)

snes_model <- snes_model %>%
  mutate(vote_in_2022 = factor(vote_in_2022, levels = parties))

# =============================================================
# 5) PREP FRAME
# =============================================================

frame_pred <- frame %>%
  rename(
    municipality_code = MunicipalityCode,
    gender            = Sex,
    age_group         = Age,
    education         = Education
  ) %>%
  mutate(
    municipality_code = as.character(municipality_code),
    gender            = recode(as.character(gender),    !!!gender_simple),
    age_group         = recode(as.character(age_group), !!!age_simple),
    education         = recode(as.character(education), !!!edu_simple)
  ) %>%
  filter(!is.na(N), N > 0)

survey_levels <- list(
  gender            = levels(snes_model$gender),
  age_group         = levels(snes_model$age_group),
  education         = levels(snes_model$education),
  municipality_code = levels(snes_model$municipality_code)
)

frame_unseen <- list(
  gender            = setdiff(unique(frame_pred$gender),            survey_levels$gender),
  age_group         = setdiff(unique(frame_pred$age_group),         survey_levels$age_group),
  education         = setdiff(unique(frame_pred$education),         survey_levels$education),
  municipality_code = setdiff(unique(frame_pred$municipality_code), survey_levels$municipality_code)
)

if (length(frame_unseen$gender) > 0)
  stop("Unseen gender levels in frame: ", paste(frame_unseen$gender, collapse = ", "))
if (length(frame_unseen$age_group) > 0)
  stop("Unseen age_group levels in frame: ", paste(frame_unseen$age_group, collapse = ", "))
if (length(frame_unseen$education) > 0)
  stop("Unseen education levels in frame: ", paste(frame_unseen$education, collapse = ", "))
if (length(frame_unseen$municipality_code) > 0)
  msg(
    length(frame_unseen$municipality_code),
    " municipalities in frame not seen in survey — these rows will be ",
    "excluded from municipality-level summaries (municipality_code → NA)."
  )

frame_pred <- frame_pred %>%
  mutate(
    gender            = factor(gender,            levels = survey_levels$gender),
    age_group         = factor(age_group,         levels = survey_levels$age_group),
    education         = factor(education,         levels = survey_levels$education),
    municipality_code = factor(municipality_code, levels = survey_levels$municipality_code)
  )

# =============================================================
# 6) INTERACTIONS
# =============================================================
add_interactions <- function(dat,
                             age_edu_levels    = NULL,
                             age_gender_levels = NULL,
                             gender_edu_levels = NULL) {
  dat$age_edu <- factor(
    paste(as.character(dat$age_group), as.character(dat$education), sep = "."),
    levels = age_edu_levels
  )
  dat$age_gender <- factor(
    paste(as.character(dat$age_group), as.character(dat$gender), sep = "."),
    levels = age_gender_levels
  )
  dat$gender_edu <- factor(
    paste(as.character(dat$gender), as.character(dat$education), sep = "."),
    levels = gender_edu_levels
  )
  dat
}

# =============================================================
# 7) STAGE DATA BUILDER
# =============================================================

make_stage_data <- function(data, party_name, vote_lookup,
                            age_edu_levels    = NULL,
                            age_gender_levels = NULL,
                            gender_edu_levels = NULL) {
  lookup_sub <- vote_lookup %>%
    filter(party == party_name) %>%
    transmute(municipality_code_chr = as.character(municipality_code),
              vote_pct_stage        = as.numeric(vote_pct))
  data %>%
    select(-any_of(c("vote_pct", "vote_pct_scaled", "vote_pct_stage",
                     "inter_age_edu", "inter_age_gender", "inter_gender_edu"))) %>%
    mutate(municipality_code_chr = as.character(municipality_code)) %>%
    left_join(lookup_sub, by = "municipality_code_chr") %>%
    mutate(
      vote_pct        = coalesce(vote_pct_stage, 0),
      vote_pct_scaled = as.numeric(scale(vote_pct)),
      vote_pct_scaled = if_else(is.na(vote_pct_scaled), 0, vote_pct_scaled)
    ) %>%
    select(-municipality_code_chr, -vote_pct_stage) %>%
    add_interactions(age_edu_levels, age_gender_levels, gender_edu_levels)
}

# =============================================================
# 8) FIT ONE STAGE
# =============================================================

fit_one_stage <- function(dat, party_name, min_n = 80, min_events = 15) {
  
  original_codes  <- as.character(dat$municipality_code)
  seq_map         <- setNames(
    seq_along(unique(original_codes)),
    unique(original_codes)
  )
  
  d <- dat %>%
    add_interactions() %>%
    mutate(
      y                 = as.integer(vote_in_2022 == party_name),
      gender            = factor(as.character(gender)),
      age_group         = factor(as.character(age_group)),
      education         = factor(as.character(education)),
      municipality_code = factor(seq_map[as.character(municipality_code)]),
      vote_in_2022      = factor(as.character(vote_in_2022))
    )
  
  n_total       <- nrow(d)
  n_event       <- sum(d$y, na.rm = TRUE)
  fallback_prob <- pmin(pmax(if (n_total > 0) n_event / n_total else 0, eps), 1 - eps)
  
  if (n_total < min_n || n_event < min_events || (n_total - n_event) < min_events) {
    return(list(fit = NULL, fallback_prob = fallback_prob,
                n_total = n_total, n_event = n_event, status = "fallback_sparse"))
  }
  
  formula_full <- if (n_total >= 300) {
    y ~ v_s(vote_pct) +
      gender + (1 | age_group) + (1 | education) +
      (1 | age_edu) + (1 | age_gender) + (1 | gender_edu)
  } else {
    y ~ v_s(vote_pct) +
      (1 | municipality_code) +
      (1 | gender) + (1 | age_group) + (1 | education)
  }
  
  fit <- tryCatch(
    vglmer(formula_full, data = d, family = "binomial",
           control = vglmer_control(iterations = 15000)),
    error = function(e) { msg("fit_full failed for ", party_name, ": ", conditionMessage(e)); NULL }
  )
  
  if (!is.null(fit)) {
    return(list(
      fit               = fit,
      fallback_prob     = fallback_prob,
      n_total           = n_total,
      n_event           = n_event,
      status            = "fit_ok_full",
      seq_map           = seq_map,
      age_edu_levels    = levels(d$inter_age_edu),
      age_gender_levels = levels(d$inter_age_gender),
      gender_edu_levels = levels(d$inter_gender_edu)
    ))
  }
  
  msg("Trying simple fallback model for ", party_name)
  fit_simple <- tryCatch(
    vglmer(
      y ~ v_s(vote_pct) + gender + (1 | age_group) + (1 | education),
      data = d, family = "binomial",
      control = vglmer_control(iterations = 5000)
    ),
    error = function(e) { msg("fit_simple also failed for ", party_name, ": ", conditionMessage(e)); NULL }
  )
  
  if (!is.null(fit_simple)) {
    return(list(
      fit               = fit_simple,
      fallback_prob     = fallback_prob,
      n_total           = n_total,
      n_event           = n_event,
      status            = "fit_ok_simple",
      seq_map           = seq_map,
      age_edu_levels    = levels(d$inter_age_edu),
      age_gender_levels = levels(d$inter_age_gender),
      gender_edu_levels = levels(d$inter_gender_edu)
    ))
  }
  
  list(fit = NULL, fallback_prob = fallback_prob,
       n_total = n_total, n_event = n_event, status = "fallback_error")
}

# =============================================================
# 9) FIT ALL STAGES
# =============================================================

sb_fits           <- vector("list", K - 1)
names(sb_fits)    <- parties[seq_len(K - 1)]
remaining_parties <- parties

for (k in seq_len(K - 1)) {
  current_party <- remaining_parties[1]
  d_k <- snes_model %>%
    filter(vote_in_2022 %in% remaining_parties) %>%
    mutate(vote_in_2022 = droplevels(vote_in_2022)) %>%
    droplevels() %>%
    make_stage_data(current_party, election_results)
  
  sb_fits[[k]] <- fit_one_stage(d_k, current_party)
  msg("Stage ", k, "/", K-1, " [", current_party, "] : ", sb_fits[[k]]$status,
      " | n=", sb_fits[[k]]$n_total, " | events=", sb_fits[[k]]$n_event)
  remaining_parties <- remaining_parties[-1]
}

# =============================================================
# 10) PREDICTION HELPERS
#     seq_map applied to newdata so municipality codes match
#     what the model was trained on
# =============================================================

prepare_newdata_muni <- function(newdata, seq_map) {
  if (is.null(seq_map)) return(newdata)
  orig <- as.character(newdata$municipality_code)
  mapped <- seq_map[orig]
  # unseen municipalities → NA (predict_MAVB handles via allow_missing_levels)
  newdata$municipality_code <- factor(mapped, levels = as.character(seq_map))
  newdata
}

predict_point <- function(stage_obj, newdata) {
  if (is.null(stage_obj$fit))
    return(rep(stage_obj$fallback_prob, nrow(newdata)))
  nd  <- prepare_newdata_muni(newdata, stage_obj$seq_map)
  eta <- tryCatch(
    predict_MAVB(stage_obj$fit, newdata = nd, samples = 1,
                 summary = TRUE, allow_missing_levels = TRUE),
    error = function(e) NULL
  )
  if (is.null(eta)) return(rep(stage_obj$fallback_prob, nrow(newdata)))
  if (is.list(eta)) eta <- eta[["mean"]] %||% eta[[1]]
  pmin(pmax(plogis(as.numeric(eta)), eps), 1 - eps)
}

predict_draws <- function(stage_obj, newdata, n_sims = 250) {
  if (is.null(stage_obj$fit))
    return(matrix(stage_obj$fallback_prob, nrow = nrow(newdata), ncol = n_sims))
  nd  <- prepare_newdata_muni(newdata, stage_obj$seq_map)
  eta <- tryCatch(
    predict_MAVB(stage_obj$fit, newdata = nd, samples = n_sims,
                 summary = FALSE, allow_missing_levels = TRUE),
    error = function(e) NULL
  )
  if (is.null(eta)) return(matrix(stage_obj$fallback_prob, nrow = nrow(newdata), ncol = n_sims))
  eta <- as.matrix(eta)
  if (nrow(eta) == n_sims) eta <- t(eta)
  pmin(pmax(plogis(eta), eps), 1 - eps)
}

# =============================================================
# 11) POSTSTRATIFICATION — POINT ESTIMATES
# =============================================================

pi_mat <- matrix(NA_real_, nrow = nrow(frame_pred), ncol = K - 1)
colnames(pi_mat) <- parties[seq_len(K - 1)]

for (k in seq_len(K - 1)) {
  stage_newdata <- make_stage_data(
    frame_pred, parties[k], election_results,
    age_edu_levels    = sb_fits[[k]]$age_edu_levels,
    age_gender_levels = sb_fits[[k]]$age_gender_levels,
    gender_edu_levels = sb_fits[[k]]$gender_edu_levels
  )
  pi_mat[, k] <- predict_point(sb_fits[[k]], stage_newdata)
}

prob_mat       <- matrix(0, nrow = nrow(frame_pred), ncol = K)
colnames(prob_mat) <- parties
remaining_mass <- rep(1, nrow(frame_pred))

for (k in seq_len(K - 1)) {
  prob_mat[, k]  <- remaining_mass * pi_mat[, k]
  remaining_mass <- remaining_mass * (1 - pi_mat[, k])
}
prob_mat[, K] <- remaining_mass
prob_mat[prob_mat < 0] <- 0

row_sums  <- rowSums(prob_mat)
bad_rows  <- which(!is.finite(row_sums) | row_sums <= 0)
if (length(bad_rows) > 0) {
  warning(length(bad_rows), " rows had invalid probability sums; replacing with uniform.")
  prob_mat[bad_rows, ] <- 1 / K
  row_sums[bad_rows]   <- 1
}
prob_mat <- prob_mat / row_sums

# =============================================================
# 12) NATIONAL POINT ESTIMATES
# =============================================================

mrp_national <- as_tibble(prob_mat) %>%
  mutate(weight = frame_pred$N) %>%
  summarise(across(-weight, ~ weighted.mean(.x, w = weight, na.rm = TRUE))) %>%
  pivot_longer(everything(), names_to = "party", values_to = "point_estimate") %>%
  arrange(desc(point_estimate))

# =============================================================
# 13) UNCERTAINTY DRAWS
# =============================================================

pi_draws <- vector("list", K - 1)
for (k in seq_len(K - 1)) {
  stage_newdata <- make_stage_data(
    frame_pred, parties[k], election_results,
    age_edu_levels    = sb_fits[[k]]$age_edu_levels,
    age_gender_levels = sb_fits[[k]]$age_gender_levels,
    gender_edu_levels = sb_fits[[k]]$gender_edu_levels
  )
  pi_draws[[k]] <- predict_draws(sb_fits[[k]], stage_newdata, n_sims)
}

share_draws        <- matrix(NA_real_, nrow = n_sims, ncol = K)
colnames(share_draws) <- parties

for (s in seq_len(n_sims)) {
  rm_s   <- rep(1, nrow(frame_pred))
  pm_s   <- matrix(0, nrow = nrow(frame_pred), ncol = K)
  colnames(pm_s) <- parties
  for (k in seq_len(K - 1)) {
    pm_s[, k] <- rm_s * pi_draws[[k]][, s]
    rm_s      <- rm_s * (1 - pi_draws[[k]][, s])
  }
  pm_s[, K] <- rm_s
  pm_s[pm_s < 0] <- 0
  rs_s <- rowSums(pm_s)
  bad  <- which(!is.finite(rs_s) | rs_s <= 0)
  if (length(bad) > 0) { pm_s[bad, ] <- 1 / K; rs_s[bad] <- 1 }
  pm_s <- pm_s / rs_s
  share_draws[s, ] <- apply(pm_s, 2, weighted.mean, w = frame_pred$N, na.rm = TRUE)
}

# =============================================================
# 14) NATIONAL QUARTILE TABLE
# =============================================================

quartile_table <- tibble(
  party          = parties,
  lower_quartile = apply(share_draws, 2, quantile, probs = 0.25, na.rm = TRUE),
  median         = apply(share_draws, 2, quantile, probs = 0.50, na.rm = TRUE),
  upper_quartile = apply(share_draws, 2, quantile, probs = 0.75, na.rm = TRUE)
) %>%
  left_join(mrp_national, by = "party") %>%
  select(party, point_estimate, lower_quartile, median, upper_quartile) %>%
  arrange(desc(point_estimate))

# =============================================================
# 15) MUNICIPALITY POINT ESTIMATES
# =============================================================

valid_rows <- !is.na(frame_pred$municipality_code)

mun_estimates <- as_tibble(prob_mat[valid_rows, , drop = FALSE]) %>%
  mutate(
    municipality_code = as.character(frame_pred$municipality_code[valid_rows]),
    N                 = frame_pred$N[valid_rows]
  ) %>%
  pivot_longer(cols = all_of(parties), names_to = "party", values_to = "prob") %>%
  mutate(expected_N = N * prob) %>%
  group_by(municipality_code, party) %>%
  summarise(
    expected_N     = sum(expected_N, na.rm = TRUE),
    total_N        = sum(N, na.rm = TRUE),
    point_estimate = expected_N / total_N,
    .groups        = "drop"
  )

# 16) Per-draw municipality × party shares

mun_valid      <- as.character(frame_pred$municipality_code[valid_rows])
weights_valid  <- frame_pred$N[valid_rows]

mun_draws_list <- vector("list", n_sims)

for (s in seq_len(n_sims)) {
  rm_s <- rep(1, nrow(frame_pred))
  pm_s <- matrix(0, nrow = nrow(frame_pred), ncol = K)
  colnames(pm_s) <- parties
  
  for (k in seq_len(K - 1)) {
    pm_s[, k] <- rm_s * pi_draws[[k]][, s]
    rm_s      <- rm_s * (1 - pi_draws[[k]][, s])
  }
  pm_s[, K] <- rm_s
  pm_s[pm_s < 0] <- 0
  rs_s <- rowSums(pm_s)
  bad  <- which(!is.finite(rs_s) | rs_s <= 0)
  if (length(bad) > 0) { pm_s[bad, ] <- 1 / K; rs_s[bad] <- 1 }
  pm_s <- pm_s / rs_s
  
  mun_draws_list[[s]] <- as_tibble(pm_s[valid_rows, , drop = FALSE]) %>%
    mutate(municipality_code = mun_valid, N = weights_valid, draw = s) %>%
    pivot_longer(cols = all_of(parties), names_to = "party", values_to = "prob") %>%
    mutate(expected_N = N * prob) %>%
    group_by(draw, municipality_code, party) %>%
    summarise(
      expected_N = sum(expected_N, na.rm = TRUE),
      total_N    = sum(N, na.rm = TRUE),
      share      = expected_N / total_N,
      .groups    = "drop"
    )
}

mun_party_draws <- bind_rows(mun_draws_list)

# 17) Municipality × party quartiles

mun_party_quartiles <- mun_party_draws %>%
  group_by(municipality_code, party) %>%
  summarise(
    lower_quartile   = quantile(share, 0.25, na.rm = TRUE),
    median           = quantile(share, 0.50, na.rm = TRUE),
    upper_quartile   = quantile(share, 0.75, na.rm = TRUE),
    sd_draws         = sd(share, na.rm = TRUE),
    .groups          = "drop"
  ) %>%
  left_join(mun_estimates, by = c("municipality_code", "party")) %>%
  select(municipality_code, party, point_estimate,
         lower_quartile, median, upper_quartile, sd_draws) %>%
  arrange(municipality_code, desc(point_estimate))

# 18) Diagnostics

stage_diagnostics <- tibble(
  stage         = seq_len(K - 1),
  party         = parties[seq_len(K - 1)],
  status        = map_chr(sb_fits, "status"),
  n_total       = map_dbl(sb_fits, "n_total"),
  n_event       = map_dbl(sb_fits, "n_event"),
  fallback_prob = map_dbl(sb_fits, "fallback_prob")
)

# =============================================================
# 19) OUTPUTS
# =============================================================

write_csv(mrp_national,      file.path(output_dir, "mrp_national_point_estimates.csv"))
write_csv(quartile_table,    file.path(output_dir, "mrp_national_quartile_table.csv"))
write_csv(stage_diagnostics, file.path(output_dir, "mrp_stage_diagnostics.csv"))
write_csv(mun_estimates,     file.path(output_dir, "mrp_municipality_point_estimates.csv"))
write_csv(mun_party_draws,   file.path(output_dir, "mrp_municipality_party_draws_250_long.csv"))
write_csv(mun_party_quartiles, file.path(output_dir, "mrp_municipality_party_quartiles.csv"))
write_csv(
  as_tibble(share_draws) %>% mutate(draw = seq_len(n())),
  file.path(output_dir, "mrp_national_share_draws.csv")
)
write_csv(
  as_tibble(prob_mat),
  file.path(output_dir, "mrp_cell_party_probabilities.csv")
)

msg("All outputs written to: ", normalizePath(output_dir))
