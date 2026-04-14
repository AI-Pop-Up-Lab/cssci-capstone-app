library(dplyr)
library(purrr)
library(readr)
library(tibble)
library(tidyr)
library(vglmer)

default_post_strat_config <- function() {
  list(
    eps = 1e-8,
    verbose = TRUE,
    n_sims = 250,
    min_n = 80,
    min_events = 15,
    seed = NULL,
    survey_aliases = list(
      past_vote = c("vote_in_2022", "party"),
      predicted_vote = c("vote_2026")
    ),
    frame_aliases = list(
      past_vote = c("vote_in_2022", "party"),
      expected_N_raked = c("expected_N")
    ),
    education_level_recode = c(
      "H1010 Primary school through to 6th grade" = "H1020 Primary school 7th-9th grade"
    )
  )
}

make_logger <- function(verbose = TRUE) {
  function(...) {
    if (isTRUE(verbose)) {
      message(...)
    }
  }
}

resolve_post_strat_config <- function(config = list()) {
  resolved <- modifyList(default_post_strat_config(), config)
  resolved$msg <- make_logger(resolved$verbose)
  resolved
}

rename_alias_columns <- function(dat, alias_map) {
  for (canonical in names(alias_map)) {
    if (canonical %in% names(dat)) {
      next
    }

    aliases <- alias_map[[canonical]]
    alias_hits <- aliases[aliases %in% names(dat)]

    if (length(alias_hits) > 0) {
      names(dat)[match(alias_hits[[1]], names(dat))] <- canonical
    }
  }

  dat
}

recode_education_level <- function(dat, recode_map) {
  if (!("education_level" %in% names(dat)) || length(recode_map) == 0) {
    return(dat)
  }

  dat %>%
    mutate(
      education_level = dplyr::recode(as.character(education_level), !!!as.list(recode_map))
    )
}

validate_required_columns <- function(dat, required, data_name) {
  missing_cols <- setdiff(required, names(dat))

  if (length(missing_cols) > 0) {
    stop("Missing columns in ", data_name, ": ", paste(missing_cols, collapse = ", "))
  }
}

resolve_party_order <- function(survey_model) {
  party_counts <- survey_model %>%
    count(predicted_vote, sort = TRUE)

  if ("Did not vote" %in% party_counts$predicted_vote) {
    c(
      "Did not vote",
      party_counts %>%
        filter(predicted_vote != "Did not vote") %>%
        pull(predicted_vote)
    )
  } else {
    party_counts %>%
      pull(predicted_vote)
  }
}

prepare_survey_data <- function(survey, config) {
  survey_required <- c(
    "age_group",
    "gender",
    "municipality",
    "education_level",
    "past_vote",
    "predicted_vote"
  )

  survey <- survey %>%
    rename_alias_columns(config$survey_aliases) %>%
    recode_education_level(config$education_level_recode)

  validate_required_columns(survey, survey_required, "survey")

  survey_model <- survey %>%
    mutate(
      age_group = as.character(age_group),
      gender = as.character(gender),
      municipality = as.character(municipality),
      education_level = as.character(education_level),
      past_vote = as.character(past_vote),
      predicted_vote = as.character(predicted_vote)
    ) %>%
    filter(if_all(all_of(survey_required), ~ !is.na(.x) & .x != ""))

  if (nrow(survey_model) == 0) {
    stop("No complete cases remain in survey after filtering required variables.")
  }

  party_order <- resolve_party_order(survey_model)

  if (length(party_order) < 2) {
    stop("Need at least two outcome categories in predicted_vote.")
  }

  survey_model <- survey_model %>%
    mutate(
      predicted_vote = factor(predicted_vote, levels = party_order),
      gender = factor(gender),
      age_group = factor(age_group),
      education_level = factor(education_level),
      municipality = factor(municipality),
      past_vote = factor(past_vote)
    )

  list(
    survey_model = survey_model,
    parties = levels(survey_model$predicted_vote)
  )
}

prepare_frame_data <- function(frame, survey_model, config) {
  frame_required <- c(
    "age_group",
    "gender",
    "municipality",
    "education_level",
    "past_vote",
    "expected_N_raked"
  )

  frame <- frame %>%
    rename_alias_columns(config$frame_aliases) %>%
    recode_education_level(config$education_level_recode)

  validate_required_columns(frame, frame_required, "frame")

  frame_pred <- frame %>%
    mutate(
      age_group = as.character(age_group),
      gender = as.character(gender),
      municipality = as.character(municipality),
      education_level = as.character(education_level),
      past_vote = as.character(past_vote),
      expected_N_raked = as.numeric(expected_N_raked)
    ) %>%
    filter(
      !is.na(age_group),
      !is.na(gender),
      !is.na(municipality),
      !is.na(education_level),
      !is.na(past_vote),
      !is.na(expected_N_raked),
      expected_N_raked > 0
    )

  if (nrow(frame_pred) == 0) {
    stop("No usable rows remain in frame after filtering.")
  }

  survey_levels <- list(
    gender = levels(survey_model$gender),
    age_group = levels(survey_model$age_group),
    education_level = levels(survey_model$education_level),
    municipality = levels(survey_model$municipality),
    past_vote = levels(survey_model$past_vote)
  )

  frame_unseen <- list(
    gender = setdiff(unique(frame_pred$gender), survey_levels$gender),
    age_group = setdiff(unique(frame_pred$age_group), survey_levels$age_group),
    education_level = setdiff(unique(frame_pred$education_level), survey_levels$education_level),
    municipality = setdiff(unique(frame_pred$municipality), survey_levels$municipality),
    past_vote = setdiff(unique(frame_pred$past_vote), survey_levels$past_vote)
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
  if (length(frame_unseen$past_vote) > 0) {
    stop("Unseen past_vote levels in frame: ", paste(frame_unseen$past_vote, collapse = ", "))
  }

  if (length(frame_unseen$municipality) > 0) {
    config$msg(
      "There are ", length(frame_unseen$municipality),
      " municipalities in the frame not seen in the survey. ",
      "These rows will be excluded from municipality-level summaries ",
      "because municipality becomes NA after factor alignment."
    )
  }

  frame_pred %>%
    mutate(
      gender = factor(gender, levels = survey_levels$gender),
      age_group = factor(age_group, levels = survey_levels$age_group),
      education_level = factor(education_level, levels = survey_levels$education_level),
      municipality = factor(municipality, levels = survey_levels$municipality),
      past_vote = factor(past_vote, levels = survey_levels$past_vote)
    )
}

add_interactions <- function(dat,
                             age_edu_levels = NULL,
                             age_gender_levels = NULL,
                             gender_edu_levels = NULL,
                             past_vote_age_levels = NULL,
                             past_vote_gender_levels = NULL,
                             past_vote_edu_levels = NULL) {
  age_edu_raw <- interaction(dat$age_group, dat$education_level, drop = TRUE, sep = "___")
  age_gender_raw <- interaction(dat$age_group, dat$gender, drop = TRUE, sep = "___")
  gender_edu_raw <- interaction(dat$gender, dat$education_level, drop = TRUE, sep = "___")
  past_vote_age_raw <- interaction(dat$past_vote, dat$age_group, drop = TRUE, sep = "___")
  past_vote_gender_raw <- interaction(dat$past_vote, dat$gender, drop = TRUE, sep = "___")
  past_vote_edu_raw <- interaction(dat$past_vote, dat$education_level, drop = TRUE, sep = "___")

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

  dat$past_vote_age <- if (is.null(past_vote_age_levels)) {
    factor(past_vote_age_raw)
  } else {
    factor(as.character(past_vote_age_raw), levels = past_vote_age_levels)
  }

  dat$past_vote_gender <- if (is.null(past_vote_gender_levels)) {
    factor(past_vote_gender_raw)
  } else {
    factor(as.character(past_vote_gender_raw), levels = past_vote_gender_levels)
  }

  dat$past_vote_edu <- if (is.null(past_vote_edu_levels)) {
    factor(past_vote_edu_raw)
  } else {
    factor(as.character(past_vote_edu_raw), levels = past_vote_edu_levels)
  }

  dat
}

fit_one_stage <- function(dat, target_party, config) {
  d <- dat %>%
    mutate(
      y = as.integer(predicted_vote == target_party),
      gender = droplevels(gender),
      age_group = droplevels(age_group),
      education_level = droplevels(education_level),
      municipality = droplevels(municipality),
      past_vote = droplevels(past_vote),
      predicted_vote = droplevels(predicted_vote)
    )

  d <- add_interactions(d)

  n_total <- nrow(d)
  n_event <- sum(d$y, na.rm = TRUE)
  use_interactions <- n_total >= 300

  fallback_prob <- if (n_total > 0) n_event / n_total else 0
  fallback_prob <- pmin(pmax(fallback_prob, config$eps), 1 - config$eps)

  if (n_total < config$min_n || n_event < config$min_events || (n_total - n_event) < config$min_events) {
    return(list(
      fit = NULL,
      fallback_prob = fallback_prob,
      n_total = n_total,
      n_event = n_event,
      status = "fallback_sparse"
    ))
  }

  formula_full <- if (use_interactions) {
    y ~
      (1 | municipality) +
      (1 | gender) +
      (1 | age_group) +
      (1 | education_level) +
      (1 | past_vote) +
      (1 | age_edu) +
      (1 | age_gender) +
      (1 | gender_edu)
  } else {
    y ~
      (1 | municipality) +
      (1 | gender) +
      (1 | age_group) +
      (1 | education_level) +
      (1 | past_vote)
  }

  fit_full <- tryCatch(
    vglmer(
      formula_full,
      data = d,
      family = "binomial",
      control = vglmer_control(iterations = 2000)
    ),
    error = function(e) {
      config$msg("fit_full failed for ", target_party)
      config$msg("  error: ", conditionMessage(e))
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
      gender_edu_levels = levels(d$gender_edu),
      past_vote_age_levels = levels(d$past_vote_age),
      past_vote_gender_levels = levels(d$past_vote_gender),
      past_vote_edu_levels = levels(d$past_vote_edu)
    ))
  }

  fit_simple <- tryCatch(
    vglmer(
      y ~ gender + age_group + education_level + municipality + past_vote,
      data = d,
      family = "binomial",
      control = vglmer_control(iterations = 2000)
    ),
    error = function(e) {
      config$msg("fit_simple failed for ", target_party, ": ", conditionMessage(e))
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

fit_stickbreaking_models <- function(survey_model, parties, config) {
  sb_fits <- vector("list", length(parties) - 1)
  names(sb_fits) <- parties[seq_len(length(parties) - 1)]
  remaining_parties <- parties

  for (k in seq_len(length(parties) - 1)) {
    current_party <- remaining_parties[[1]]

    d_k <- survey_model %>%
      filter(predicted_vote %in% remaining_parties) %>%
      mutate(predicted_vote = droplevels(predicted_vote)) %>%
      droplevels()

    stage_fit <- fit_one_stage(d_k, current_party, config)
    sb_fits[[k]] <- stage_fit

    config$msg(
      "Stage ", k, "/", length(parties) - 1, " [", current_party, "] : ",
      stage_fit$status, " | n=", stage_fit$n_total,
      " | events=", stage_fit$n_event,
      " | fallback=", round(stage_fit$fallback_prob, 6)
    )

    remaining_parties <- remaining_parties[-1]
  }

  sb_fits
}

predict_stage_point <- function(stage_obj, newdata, config) {
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
      config$msg("Point prediction failed; reverting to fallback: ", conditionMessage(e))
      e
    }
  )

  if (inherits(eta, "error")) {
    return(rep(stage_obj$fallback_prob, nrow(newdata)))
  }

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
      config$msg("Unknown list structure from predict_MAVB(); using fallback")
      return(rep(stage_obj$fallback_prob, nrow(newdata)))
    }
  }

  eta <- as.numeric(eta)
  p <- plogis(eta)
  pmin(pmax(p, config$eps), 1 - config$eps)
}

predict_stage_draws <- function(stage_obj, newdata, config) {
  if (is.null(stage_obj$fit)) {
    return(matrix(stage_obj$fallback_prob, nrow = nrow(newdata), ncol = config$n_sims))
  }

  eta_draws <- tryCatch(
    predict_MAVB(
      stage_obj$fit,
      newdata = newdata,
      samples = config$n_sims,
      summary = FALSE,
      allow_missing_levels = TRUE
    ),
    error = function(e) e
  )

  if (inherits(eta_draws, "error")) {
    config$msg("Simulation prediction failed; reverting to fallback: ", conditionMessage(eta_draws))
    return(matrix(stage_obj$fallback_prob, nrow = nrow(newdata), ncol = config$n_sims))
  }

  eta_draws <- as.matrix(eta_draws)

  if (nrow(eta_draws) == config$n_sims && ncol(eta_draws) == nrow(newdata)) {
    eta_draws <- t(eta_draws)
  } else if (!(nrow(eta_draws) == nrow(newdata) && ncol(eta_draws) == config$n_sims)) {
    stop(
      "Unexpected dimensions from predict_MAVB(): got ",
      nrow(eta_draws), " x ", ncol(eta_draws),
      ", expected either ", nrow(newdata), " x ", config$n_sims,
      " or ", config$n_sims, " x ", nrow(newdata), "."
    )
  }

  p_draws <- plogis(eta_draws)
  pmin(pmax(p_draws, config$eps), 1 - config$eps)
}

make_prediction_data <- function(data, stage_obj) {
  add_interactions(
    data,
    age_edu_levels = stage_obj$age_edu_levels,
    age_gender_levels = stage_obj$age_gender_levels,
    gender_edu_levels = stage_obj$gender_edu_levels,
    past_vote_age_levels = stage_obj$past_vote_age_levels,
    past_vote_gender_levels = stage_obj$past_vote_gender_levels,
    past_vote_edu_levels = stage_obj$past_vote_edu_levels
  )
}

normalize_probability_matrix <- function(prob_mat) {
  n_parties <- ncol(prob_mat)
  prob_mat[prob_mat < 0] <- 0
  row_sums <- rowSums(prob_mat)
  bad_rows <- which(!is.finite(row_sums) | row_sums <= 0)

  if (length(bad_rows) > 0) {
    warning(length(bad_rows), " rows had invalid probability sums; replacing with uniform distribution.")
    prob_mat[bad_rows, ] <- 1 / n_parties
    row_sums[bad_rows] <- 1
  }

  prob_mat / row_sums
}

build_probability_matrix <- function(pi_components, parties) {
  n_rows <- nrow(pi_components[[1]])
  n_parties <- length(parties)
  prob_mat <- matrix(0, nrow = n_rows, ncol = n_parties)
  colnames(prob_mat) <- parties
  remaining_mass <- rep(1, n_rows)

  for (k in seq_len(n_parties - 1)) {
    prob_mat[, k] <- remaining_mass * pi_components[[k]]
    remaining_mass <- remaining_mass * (1 - pi_components[[k]])
  }

  prob_mat[, n_parties] <- remaining_mass
  normalize_probability_matrix(prob_mat)
}

compute_national_point_estimates <- function(prob_mat, weights) {
  as_tibble(prob_mat) %>%
    mutate(weight = weights) %>%
    summarise(across(-weight, ~ weighted.mean(.x, w = weight, na.rm = TRUE))) %>%
    pivot_longer(
      everything(),
      names_to = "party",
      values_to = "point_estimate"
    ) %>%
    arrange(desc(point_estimate))
}

compute_share_draws <- function(pi_draws, parties, weights) {
  share_draws <- matrix(NA_real_, nrow = ncol(pi_draws[[1]]), ncol = length(parties))
  colnames(share_draws) <- parties

  for (s in seq_len(ncol(pi_draws[[1]]))) {
    pi_components_s <- lapply(pi_draws, function(draw_mat) draw_mat[, s, drop = FALSE])
    prob_mat_s <- build_probability_matrix(pi_components_s, parties)

    share_draws[s, ] <- apply(
      prob_mat_s,
      2,
      weighted.mean,
      w = weights,
      na.rm = TRUE
    )
  }

  share_draws
}

build_quartile_table <- function(share_draws, parties, mrp_estimates) {
  tibble(
    party = parties,
    lower_quartile = apply(share_draws, 2, quantile, probs = 0.25, na.rm = TRUE),
    median = apply(share_draws, 2, quantile, probs = 0.50, na.rm = TRUE),
    upper_quartile = apply(share_draws, 2, quantile, probs = 0.75, na.rm = TRUE)
  ) %>%
    left_join(mrp_estimates, by = "party") %>%
    select(party, point_estimate, lower_quartile, median, upper_quartile) %>%
    arrange(desc(point_estimate))
}

build_extended_frame <- function(prob_mat, frame_pred) {
  frame_for_join <- frame_pred %>%
    transmute(
      cell_id = seq_len(n()),
      age_group,
      gender,
      municipality,
      past_vote,
      education_level,
      expected_N_raked
    )

  as_tibble(prob_mat) %>%
    mutate(cell_id = seq_len(nrow(frame_pred))) %>%
    pivot_longer(
      cols = -cell_id,
      names_to = "predicted_vote_party",
      values_to = "prob"
    ) %>%
    left_join(frame_for_join, by = "cell_id") %>%
    mutate(expected_N = expected_N_raked * prob) %>%
    select(
      cell_id,
      age_group,
      gender,
      municipality,
      past_vote,
      education_level,
      expected_N_raked,
      predicted_vote_party,
      prob,
      expected_N
    )
}

compute_stage_diagnostics <- function(sb_fits, parties) {
  tibble(
    stage = seq_len(length(parties) - 1),
    party = parties[seq_len(length(parties) - 1)],
    status = map_chr(sb_fits, "status"),
    n_total = map_dbl(sb_fits, "n_total"),
    n_event = map_dbl(sb_fits, "n_event"),
    fallback_prob = map_dbl(sb_fits, "fallback_prob")
  )
}

compute_aggregate_counts <- function(extended_frame) {
  extended_frame %>%
    group_by(predicted_vote_party) %>%
    summarise(
      expected_total = sum(expected_N, na.rm = TRUE),
      expected_share = sum(expected_N, na.rm = TRUE) / sum(expected_N_raked[!duplicated(cell_id)]),
      .groups = "drop"
    ) %>%
    arrange(desc(expected_share))
}

compute_municipality_point <- function(prob_mat, frame_pred, parties) {
  valid_rows <- !is.na(frame_pred$municipality)

  as_tibble(prob_mat[valid_rows, , drop = FALSE]) %>%
    mutate(
      municipality = as.character(frame_pred$municipality[valid_rows]),
      weight = frame_pred$expected_N_raked[valid_rows]
    ) %>%
    pivot_longer(
      cols = all_of(parties),
      names_to = "predicted_vote_party",
      values_to = "prob"
    ) %>%
    mutate(expected_N = weight * prob) %>%
    group_by(municipality, predicted_vote_party) %>%
    summarise(
      expected_N = sum(expected_N, na.rm = TRUE),
      total_N = sum(weight, na.rm = TRUE),
      point_estimate = expected_N / total_N,
      .groups = "drop"
    )
}

compute_municipality_draws <- function(pi_draws, frame_pred, parties) {
  valid_rows <- !is.na(frame_pred$municipality)
  municipality_valid <- as.character(frame_pred$municipality[valid_rows])
  weights_valid <- frame_pred$expected_N_raked[valid_rows]

  bind_rows(lapply(seq_len(ncol(pi_draws[[1]])), function(s) {
    pi_components_s <- lapply(pi_draws, function(draw_mat) draw_mat[, s, drop = FALSE])
    prob_mat_s <- build_probability_matrix(pi_components_s, parties)

    as_tibble(prob_mat_s[valid_rows, , drop = FALSE]) %>%
      mutate(
        municipality = municipality_valid,
        weight = weights_valid,
        draw = s
      ) %>%
      pivot_longer(
        cols = all_of(parties),
        names_to = "predicted_vote_party",
        values_to = "prob"
      ) %>%
      mutate(expected_N = weight * prob) %>%
      group_by(draw, municipality, predicted_vote_party) %>%
      summarise(
        expected_N = sum(expected_N, na.rm = TRUE),
        total_N = sum(weight, na.rm = TRUE),
        share = expected_N / total_N,
        .groups = "drop"
      )
  }))
}

compute_municipality_quartiles <- function(municipality_party_draws, municipality_party_point) {
  municipality_party_draws %>%
    group_by(municipality, predicted_vote_party) %>%
    summarise(
      lower_quartile = quantile(share, probs = 0.25, na.rm = TRUE),
      median = quantile(share, probs = 0.50, na.rm = TRUE),
      upper_quartile = quantile(share, probs = 0.75, na.rm = TRUE),
      sd_draws = sd(share, na.rm = TRUE),
      n_distinct_draws = n_distinct(share),
      .groups = "drop"
    ) %>%
    left_join(municipality_party_point, by = c("municipality", "predicted_vote_party")) %>%
    select(
      municipality,
      predicted_vote_party,
      point_estimate,
      lower_quartile,
      median,
      upper_quartile,
      sd_draws,
      n_distinct_draws
    ) %>%
    arrange(municipality, desc(point_estimate))
}

build_share_draws_long <- function(share_draws) {
  as_tibble(share_draws) %>%
    mutate(draw = seq_len(n())) %>%
    pivot_longer(
      cols = -draw,
      names_to = "predicted_vote_party",
      values_to = "share"
    )
}

run_post_stratification <- function(survey, frame, config = list()) {
  config <- resolve_post_strat_config(config)
  metadata_config <- config
  metadata_config$msg <- NULL

  if (!is.null(config$seed)) {
    set.seed(config$seed)
  }

  prepared_survey <- prepare_survey_data(survey, config)
  survey_model <- prepared_survey$survey_model
  parties <- prepared_survey$parties
  frame_pred <- prepare_frame_data(frame, survey_model, config)
  sb_fits <- fit_stickbreaking_models(survey_model, parties, config)

  pi_mat <- matrix(NA_real_, nrow = nrow(frame_pred), ncol = length(parties) - 1)
  colnames(pi_mat) <- parties[seq_len(length(parties) - 1)]

  for (k in seq_len(length(parties) - 1)) {
    stage_newdata <- make_prediction_data(frame_pred, sb_fits[[k]])
    pi_mat[, k] <- predict_stage_point(sb_fits[[k]], stage_newdata, config)
  }

  pi_components <- lapply(seq_len(ncol(pi_mat)), function(k) pi_mat[, k, drop = FALSE])
  prob_mat <- build_probability_matrix(pi_components, parties)
  weights <- frame_pred$expected_N_raked
  mrp_estimates <- compute_national_point_estimates(prob_mat, weights)

  pi_draws <- vector("list", length(parties) - 1)

  for (k in seq_len(length(parties) - 1)) {
    config$msg("Simulation draws for stage ", k, "/", length(parties) - 1, " [", parties[[k]], "]")
    stage_newdata <- make_prediction_data(frame_pred, sb_fits[[k]])
    pi_draws[[k]] <- predict_stage_draws(sb_fits[[k]], stage_newdata, config)
  }

  share_draws <- compute_share_draws(pi_draws, parties, weights)
  quartile_table <- build_quartile_table(share_draws, parties, mrp_estimates)
  extended_frame <- build_extended_frame(prob_mat, frame_pred)
  stage_diagnostics <- compute_stage_diagnostics(sb_fits, parties)
  aggregate_counts <- compute_aggregate_counts(extended_frame)
  municipality_party_point <- compute_municipality_point(prob_mat, frame_pred, parties)
  municipality_party_draws <- compute_municipality_draws(pi_draws, frame_pred, parties)
  municipality_party_quartiles <- compute_municipality_quartiles(
    municipality_party_draws,
    municipality_party_point
  )
  share_draws_long <- build_share_draws_long(share_draws)

  list(
    point_estimates = mrp_estimates,
    quartile_table = quartile_table,
    extended_frame = extended_frame,
    stage_diagnostics = stage_diagnostics,
    aggregate_counts = aggregate_counts,
    share_draws = as_tibble(share_draws),
    share_draws_long = share_draws_long,
    cell_party_probabilities = as_tibble(prob_mat),
    stickbreaking_conditional_probs = as_tibble(pi_mat),
    municipality_party_point = municipality_party_point,
    municipality_party_draws = municipality_party_draws,
    municipality_party_quartiles = municipality_party_quartiles,
    metadata = list(
      parties = parties,
      config = metadata_config
    )
  )
}

write_post_strat_outputs <- function(result, output_dir) {
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }

  write_csv(result$point_estimates, file.path(output_dir, "mrp_point_estimates.csv"))
  write_csv(result$quartile_table, file.path(output_dir, "mrp_quartile_table.csv"))
  write_csv(result$extended_frame, file.path(output_dir, "mrp_extended_frame_predictions.csv"))
  write_csv(result$stage_diagnostics, file.path(output_dir, "mrp_stage_diagnostics.csv"))
  write_csv(result$aggregate_counts, file.path(output_dir, "mrp_aggregate_counts.csv"))
  write_csv(result$share_draws, file.path(output_dir, "mrp_share_draws.csv"))
  write_csv(result$share_draws_long, file.path(output_dir, "mrp_share_draws_long.csv"))
  write_csv(result$cell_party_probabilities, file.path(output_dir, "mrp_cell_party_probabilities.csv"))
  write_csv(
    result$stickbreaking_conditional_probs,
    file.path(output_dir, "mrp_stickbreaking_conditional_probs.csv")
  )
  write_csv(
    result$municipality_party_point,
    file.path(output_dir, "mrp_municipality_party_point_estimates.csv")
  )
  write_csv(
    result$municipality_party_draws,
    file.path(output_dir, "mrp_municipality_party_draws_long.csv")
  )
  write_csv(
    result$municipality_party_quartiles,
    file.path(output_dir, "mrp_municipality_party_quartiles.csv")
  )

  invisible(result)
}
