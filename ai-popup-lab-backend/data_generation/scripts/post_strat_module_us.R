library(dplyr)
library(purrr)
library(readr)
library(tibble)
library(tidyr)
library(vglmer)

default_us_post_strat_config <- function() {
	list(
		eps = 1e-8,
		verbose = TRUE,
		n_sims = 250,
		min_n = 80,
		min_events = 15,
		seed = NULL,
		drop_other_gender = TRUE,
		survey_aliases = list(
			age_group = c("age_cat"),
			gender = c("gender_cat"),
			race = c("race_cat"),
			education_level = c("educ_cat", "education", "educ"),
			vote_2026 = c("vote_2026", "predicted_vote")
		),
		frame_aliases = list(
			age_group = c("age_cat"),
			gender = c("gender_cat"),
			race = c("race_cat"),
			education_level = c("educ_cat", "education", "educ"),
			expected_N_raked = c("expected_N_raked", "raked_weight", "expected_N", "N", "cell_pop")
		)
	)
}

make_us_post_logger <- function(verbose = TRUE) {
	function(...) {
		if (isTRUE(verbose)) {
			message(...)
		}
	}
}

resolve_us_post_strat_config <- function(config = list()) {
	resolved <- modifyList(default_us_post_strat_config(), config)
	resolved$msg <- make_us_post_logger(resolved$verbose)
	resolved
}

rename_us_post_alias_columns <- function(dat, alias_map) {
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

drop_us_post_index_columns <- function(dat) {
	dat %>%
		select(-matches("^(\\.\\.\\.1|Unnamed: 0(\\.1)?|X)$"))
}

validate_us_post_required_columns <- function(dat, required, data_name) {
	missing_cols <- setdiff(required, names(dat))

	if (length(missing_cols) > 0) {
		stop("Missing columns in ", data_name, ": ", paste(missing_cols, collapse = ", "))
	}
}

resolve_us_post_party_order <- function(survey_model) {
	party_counts <- survey_model %>%
		count(vote_2026, sort = TRUE) %>%
		pull(vote_2026)

	if ("Did not vote" %in% party_counts) {
		c("Did not vote", setdiff(party_counts, "Did not vote"))
	} else {
		party_counts
	}
}

prepare_us_post_survey_data <- function(survey, config) {
	survey_required <- c(
		"age_group",
		"gender",
		"race",
		"education_level",
		"state_abbrv",
		"state_cd",
		"vote_2026"
	)

	survey <- survey %>%
		drop_us_post_index_columns() %>%
		rename_us_post_alias_columns(config$survey_aliases)

	validate_us_post_required_columns(survey, survey_required, "survey")

	if (isTRUE(config$drop_other_gender) && "gender" %in% names(survey)) {
		survey <- survey %>%
			filter(gender != "Other")
	}

	survey_model <- survey %>%
		mutate(
			age_group = as.character(age_group),
			gender = as.character(gender),
			race = as.character(race),
			education_level = as.character(education_level),
			state_abbrv = as.character(state_abbrv),
			state_cd = as.character(state_cd),
				vote_2026 = as.character(vote_2026)
		) %>%
		filter(if_all(all_of(survey_required), ~ !is.na(.x) & .x != ""))

	if (nrow(survey_model) == 0) {
		stop("No complete cases remain in survey after filtering model variables.")
	}

	party_order <- resolve_us_post_party_order(survey_model)

	if (length(party_order) < 2) {
		stop("Need at least two outcome categories in vote_2026 after filtering.")
	}

	survey_model %>%
		mutate(
			vote_2026 = factor(vote_2026, levels = party_order),
			age_group = factor(age_group),
			gender = factor(gender),
			race = factor(race),
			education_level = factor(education_level),
			state_abbrv = factor(state_abbrv),
			state_cd = factor(state_cd)
		)
}

prepare_us_post_frame_data <- function(frame, survey_model, config) {
	frame_required <- c(
		"age_group",
		"gender",
		"race",
		"education_level",
		"state_abbrv",
		"state_cd",
		"expected_N_raked"
	)

	frame <- frame %>%
		drop_us_post_index_columns() %>%
		rename_us_post_alias_columns(config$frame_aliases)

	validate_us_post_required_columns(frame, frame_required, "frame")

	frame_pred <- frame %>%
		mutate(
			age_group = as.character(age_group),
			gender = as.character(gender),
			race = as.character(race),
			education_level = as.character(education_level),
			state_abbrv = as.character(state_abbrv),
			state_cd = as.character(state_cd),
			expected_N_raked = as.numeric(expected_N_raked)
		) %>%
		filter(
			!is.na(age_group),
			!is.na(gender),
			!is.na(race),
			!is.na(education_level),
			!is.na(state_abbrv),
			!is.na(state_cd),
			!is.na(expected_N_raked),
			expected_N_raked > 0
		)

	if (nrow(frame_pred) == 0) {
		stop("No usable rows remain in frame after filtering.")
	}

	survey_levels <- list(
		age_group = levels(survey_model$age_group),
		gender = levels(survey_model$gender),
		race = levels(survey_model$race),
		education_level = levels(survey_model$education_level),
		state_abbrv = levels(survey_model$state_abbrv),
		state_cd = levels(survey_model$state_cd)
	)

	frame_unseen <- list(
		age_group = setdiff(unique(frame_pred$age_group), survey_levels$age_group),
		gender = setdiff(unique(frame_pred$gender), survey_levels$gender),
		race = setdiff(unique(frame_pred$race), survey_levels$race),
		education_level = setdiff(unique(frame_pred$education_level), survey_levels$education_level)
	)

	if (length(frame_unseen$age_group) > 0) {
		stop("Unseen age_group levels in frame: ", paste(frame_unseen$age_group, collapse = ", "))
	}
	if (length(frame_unseen$gender) > 0) {
		stop("Unseen gender levels in frame: ", paste(frame_unseen$gender, collapse = ", "))
	}
	if (length(frame_unseen$race) > 0) {
		stop("Unseen race levels in frame: ", paste(frame_unseen$race, collapse = ", "))
	}
	if (length(frame_unseen$education_level) > 0) {
		stop("Unseen education levels in frame: ", paste(frame_unseen$education_level, collapse = ", "))
	}

	frame_pred %>%
		mutate(
			age_group = factor(age_group, levels = survey_levels$age_group),
			gender = factor(gender, levels = survey_levels$gender),
			race = factor(race, levels = survey_levels$race),
			education_level = factor(education_level, levels = survey_levels$education_level),
			state_abbrv = factor(state_abbrv, levels = survey_levels$state_abbrv),
			state_cd = factor(state_cd, levels = survey_levels$state_cd)
		)
}

add_us_post_interactions <- function(dat,
																		race_edu_levels = NULL,
																		race_gender_levels = NULL,
																		gender_edu_levels = NULL,
																		race_age_levels = NULL,
																		age_edu_levels = NULL,
																		age_gender_levels = NULL) {
	race_edu_raw <- interaction(dat$race, dat$education_level, drop = TRUE, sep = "___")
	race_gender_raw <- interaction(dat$race, dat$gender, drop = TRUE, sep = "___")
	gender_edu_raw <- interaction(dat$gender, dat$education_level, drop = TRUE, sep = "___")
	race_age_raw <- interaction(dat$race, dat$age_group, drop = TRUE, sep = "___")
	age_edu_raw <- interaction(dat$age_group, dat$education_level, drop = TRUE, sep = "___")
	age_gender_raw <- interaction(dat$age_group, dat$gender, drop = TRUE, sep = "___")

	dat$race_edu <- if (is.null(race_edu_levels)) {
		factor(race_edu_raw)
	} else {
		factor(as.character(race_edu_raw), levels = race_edu_levels)
	}

	dat$race_gender <- if (is.null(race_gender_levels)) {
		factor(race_gender_raw)
	} else {
		factor(as.character(race_gender_raw), levels = race_gender_levels)
	}

	dat$gender_edu <- if (is.null(gender_edu_levels)) {
		factor(gender_edu_raw)
	} else {
		factor(as.character(gender_edu_raw), levels = gender_edu_levels)
	}

	dat$race_age <- if (is.null(race_age_levels)) {
		factor(race_age_raw)
	} else {
		factor(as.character(race_age_raw), levels = race_age_levels)
	}

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

	dat
}

make_us_post_prediction_data <- function(data, stage_obj) {
	add_us_post_interactions(
		data,
		race_edu_levels = stage_obj$race_edu_levels,
		race_gender_levels = stage_obj$race_gender_levels,
		gender_edu_levels = stage_obj$gender_edu_levels,
		race_age_levels = stage_obj$race_age_levels,
		age_edu_levels = stage_obj$age_edu_levels,
		age_gender_levels = stage_obj$age_gender_levels
	)
}

fit_us_post_stage <- function(dat, party_name, config) {
	d <- dat %>%
		mutate(
			y = as.integer(vote_2026 == party_name),
			age_group = droplevels(age_group),
			gender = droplevels(gender),
			race = droplevels(race),
			education_level = droplevels(education_level),
			state_abbrv = droplevels(state_abbrv),
			state_cd = droplevels(state_cd),
			vote_2026 = droplevels(vote_2026)
		)

	d <- add_us_post_interactions(d)

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
			(1 | state_abbrv) +
			(1 | state_cd) +
			(1 | gender) +
			(1 | race) +
			(1 | age_group) +
			(1 | education_level) +
			(1 | race_edu) +
			(1 | race_gender) +
			(1 | gender_edu) +
			(1 | race_age) +
			(1 | age_edu) +
			(1 | age_gender)
	} else {
		y ~
			(1 | state_abbrv) +
			(1 | state_cd) +
			(1 | gender) +
			(1 | race) +
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
			config$msg("fit_full failed for ", party_name, ". Error: ", conditionMessage(e))
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
			race_edu_levels = levels(d$race_edu),
			race_gender_levels = levels(d$race_gender),
			gender_edu_levels = levels(d$gender_edu),
			race_age_levels = levels(d$race_age),
			age_edu_levels = levels(d$age_edu),
			age_gender_levels = levels(d$age_gender)
		))
	}

	fit_simple <- tryCatch(
		vglmer(
			y ~ age_group + gender + race + education_level + state_abbrv + state_cd,
			data = d,
			family = "binomial",
			control = vglmer_control(iterations = 5000)
		),
		error = function(e) {
			config$msg("fit_simple failed for ", party_name, ": ", conditionMessage(e))
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

fit_us_post_stickbreaking_models <- function(survey_model, parties, config) {
	sb_fits <- vector("list", length(parties) - 1)
	names(sb_fits) <- parties[seq_len(length(parties) - 1)]
	remaining_parties <- parties

	for (k in seq_len(length(parties) - 1)) {
		current_party <- remaining_parties[[1]]

		d_k <- survey_model %>%
			filter(vote_2026 %in% remaining_parties) %>%
			mutate(vote_2026 = droplevels(vote_2026)) %>%
			droplevels()

		stage_fit <- fit_us_post_stage(d_k, current_party, config)
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

predict_us_post_stage_point <- function(stage_obj, newdata, config) {
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

predict_us_post_stage_draws <- function(stage_obj, newdata, config) {
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

normalize_us_post_probability_matrix <- function(prob_mat) {
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

build_us_post_probability_matrix <- function(pi_components, parties) {
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
	normalize_us_post_probability_matrix(prob_mat)
}

compute_us_post_national_point_estimates <- function(prob_mat, weights) {
	as_tibble(prob_mat) %>%
		mutate(weight = weights) %>%
		summarise(across(-weight, ~ weighted.mean(.x, w = weight, na.rm = TRUE))) %>%
		pivot_longer(everything(), names_to = "vote_2026", values_to = "point_estimate") %>%
		arrange(desc(point_estimate))
}

compute_us_post_share_draws <- function(pi_draws, parties, weights) {
	share_draws <- matrix(NA_real_, nrow = ncol(pi_draws[[1]]), ncol = length(parties))
	colnames(share_draws) <- parties

	for (s in seq_len(ncol(pi_draws[[1]]))) {
		pi_components_s <- lapply(pi_draws, function(draw_mat) draw_mat[, s, drop = FALSE])
		prob_mat_s <- build_us_post_probability_matrix(pi_components_s, parties)

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

build_us_post_quartile_table <- function(share_draws, parties, mrp_estimates) {
	tibble(
		vote_2026 = parties,
		lower_quartile = apply(share_draws, 2, quantile, probs = 0.25, na.rm = TRUE),
		median = apply(share_draws, 2, quantile, probs = 0.50, na.rm = TRUE),
		upper_quartile = apply(share_draws, 2, quantile, probs = 0.75, na.rm = TRUE)
	) %>%
		left_join(mrp_estimates, by = "vote_2026") %>%
		select(vote_2026, point_estimate, lower_quartile, median, upper_quartile) %>%
		arrange(desc(point_estimate))
}

build_us_post_share_draws_quartiles <- function(share_draws, parties, mrp_estimates) {
	tibble(
		vote_2026 = parties,
		lower_2_5 = apply(share_draws, 2, quantile, probs = 0.025, na.rm = TRUE),
		upper_97_5 = apply(share_draws, 2, quantile, probs = 0.975, na.rm = TRUE)
	) %>%
		left_join(mrp_estimates, by = "vote_2026") %>%
		select(vote_2026, point_estimate, lower_2_5, upper_97_5) %>%
		arrange(desc(point_estimate))
}

build_us_post_extended_frame <- function(prob_mat, frame_pred) {
	as_tibble(prob_mat) %>%
		mutate(cell_id = seq_len(nrow(frame_pred))) %>%
		pivot_longer(cols = -cell_id, names_to = "vote_2026", values_to = "prob") %>%
		left_join(frame_pred %>% mutate(cell_id = seq_len(n())), by = "cell_id") %>%
		mutate(expected_N = expected_N_raked * prob) %>%
		select(cell_id, age_group, gender, race, state_abbrv, state_cd, education_level, expected_N_raked, vote_2026, prob, expected_N)
}

compute_us_post_stage_diagnostics <- function(sb_fits, parties) {
	tibble(
		stage = seq_len(length(parties) - 1),
		vote_2026 = parties[seq_len(length(parties) - 1)],
		status = map_chr(sb_fits, "status"),
		n_total = map_dbl(sb_fits, "n_total"),
		n_event = map_dbl(sb_fits, "n_event"),
		fallback_prob = map_dbl(sb_fits, "fallback_prob")
	)
}

compute_us_post_aggregate_counts <- function(extended_frame) {
	extended_frame %>%
		group_by(vote_2026) %>%
		summarise(
			expected_total = sum(expected_N, na.rm = TRUE),
			expected_share = sum(expected_N, na.rm = TRUE) / sum(expected_N_raked[!duplicated(cell_id)]),
			.groups = "drop"
		) %>%
		arrange(desc(expected_share))
}

compute_us_post_cd_point <- function(prob_mat, frame_pred, parties) {
	valid_rows <- !is.na(frame_pred$state_cd)

	as_tibble(prob_mat[valid_rows, , drop = FALSE]) %>%
		mutate(
			state_cd = as.character(frame_pred$state_cd[valid_rows]),
			expected_N_raked = frame_pred$expected_N_raked[valid_rows]
		) %>%
		pivot_longer(
			cols = all_of(parties),
			names_to = "vote_2026",
			values_to = "prob"
		) %>%
		mutate(expected_N = expected_N_raked * prob) %>%
		group_by(state_cd, vote_2026) %>%
		summarise(
			expected_N = sum(expected_N, na.rm = TRUE),
			total_N = sum(expected_N_raked, na.rm = TRUE),
			point_estimate = expected_N / total_N,
			.groups = "drop"
		)
}

compute_us_post_cd_draws <- function(pi_draws, frame_pred, parties) {
	cd_col <- intersect(c("state_cd", "cd", "CD", "district_id", "district"), colnames(frame_pred))[1]
	if (is.na(cd_col)) {
		cd_col <- colnames(frame_pred)[grepl("cd|district", colnames(frame_pred), ignore.case = TRUE)][1]
	}
	if (is.na(cd_col) || !cd_col %in% colnames(frame_pred)) {
		stop("Error: Could not find a Congressional District column in your post-stratification frame.")
	}

	if (length(pi_draws) == 0 || is.null(pi_draws[[1]])) {
		stop("Error: pi_draws is empty. No simulation draws were found to process.")
	}

	test_mat <- pi_draws[[1]]
	n_frame <- nrow(frame_pred)

	if (nrow(test_mat) == n_frame) {
		n_sims <- ncol(test_mat)
		transposed <- FALSE
	} else if (ncol(test_mat) == n_frame) {
		n_sims <- nrow(test_mat)
		transposed <- TRUE
	} else {
		n_sims <- ncol(test_mat)
		transposed <- FALSE
	}

	if (is.null(n_sims) || n_sims == 0) {
		stop("Error: The number of simulated draws is 0. Ensure 'n_sims' is set to a positive integer.")
	}

	valid_rows <- !is.na(frame_pred[[cd_col]])

	draws_list <- lapply(seq_len(n_sims), function(s) {
		pi_components_s <- lapply(pi_draws, function(draw_mat) {
			if (transposed) {
				matrix(draw_mat[s, valid_rows], ncol = 1)
			} else {
				matrix(draw_mat[valid_rows, s], ncol = 1)
			}
		})

		prob_mat_s <- build_us_post_probability_matrix(pi_components_s, parties)

		prob_df <- as_tibble(prob_mat_s)
		prob_df[[cd_col]] <- as.character(frame_pred[[cd_col]][valid_rows])
		prob_df$expected_N_raked <- frame_pred$expected_N_raked[valid_rows]
		prob_df$draw_id <- s

		prob_df %>%
			pivot_longer(cols = all_of(parties), names_to = "vote_2026", values_to = "prob") %>%
			mutate(expected_N = expected_N_raked * prob) %>%
			group_by(.data[[cd_col]], vote_2026, draw_id) %>%
			summarise(
				draw_share = sum(expected_N, na.rm = TRUE) / sum(expected_N_raked, na.rm = TRUE),
				.groups = "drop"
			)
	})

	bind_rows(draws_list)
}

compute_us_post_cd_quartiles <- function(cd_party_draws, cd_party_point) {
	cd_party_draws %>%
		group_by(state_cd, vote_2026) %>%
		summarise(
			lower_quartile = quantile(draw_share, probs = 0.25, na.rm = TRUE),
			median = quantile(draw_share, probs = 0.50, na.rm = TRUE),
			upper_quartile = quantile(draw_share, probs = 0.75, na.rm = TRUE),
			sd_draws = sd(draw_share, na.rm = TRUE),
			n_distinct_draws = n_distinct(draw_share),
			.groups = "drop"
		) %>%
		left_join(cd_party_point, by = c("state_cd", "vote_2026")) %>%
		select(
			state_cd,
			vote_2026,
			point_estimate,
			lower_quartile,
			median,
			upper_quartile,
			sd_draws,
			n_distinct_draws
		) %>%
		arrange(state_cd, desc(point_estimate))
}

build_us_post_share_draws_long <- function(share_draws) {
	as_tibble(share_draws) %>%
		mutate(draw = seq_len(n())) %>%
		pivot_longer(
			cols = -draw,
			names_to = "vote_2026",
			values_to = "share"
		)
}

run_post_stratification <- function(survey, frame, config = list()) {
	config <- resolve_us_post_strat_config(config)
	metadata_config <- config
	metadata_config$msg <- NULL

	if (!is.null(config$seed)) {
		set.seed(config$seed)
	}

	survey_model <- prepare_us_post_survey_data(survey, config)
	parties <- levels(survey_model$vote_2026)
	frame_pred <- prepare_us_post_frame_data(frame, survey_model, config)
	sb_fits <- fit_us_post_stickbreaking_models(survey_model, parties, config)

	pi_mat <- matrix(NA_real_, nrow = nrow(frame_pred), ncol = length(parties) - 1)
	colnames(pi_mat) <- parties[seq_len(length(parties) - 1)]

	for (k in seq_len(length(parties) - 1)) {
		stage_newdata <- make_us_post_prediction_data(frame_pred, sb_fits[[k]])
		pi_mat[, k] <- predict_us_post_stage_point(sb_fits[[k]], stage_newdata, config)
	}

	pi_components <- lapply(seq_len(ncol(pi_mat)), function(k) pi_mat[, k, drop = FALSE])
	prob_mat <- build_us_post_probability_matrix(pi_components, parties)
	weights <- frame_pred$expected_N_raked
	mrp_estimates <- compute_us_post_national_point_estimates(prob_mat, weights)

	pi_draws <- vector("list", length(parties) - 1)

	for (k in seq_len(length(parties) - 1)) {
		config$msg("Simulation draws for stage ", k, "/", length(parties) - 1, " [", parties[[k]], "]")
		stage_newdata <- make_us_post_prediction_data(frame_pred, sb_fits[[k]])
		pi_draws[[k]] <- predict_us_post_stage_draws(sb_fits[[k]], stage_newdata, config)
	}

	share_draws <- compute_us_post_share_draws(pi_draws, parties, weights)
	quartile_table <- build_us_post_quartile_table(share_draws, parties, mrp_estimates)
	share_draws_quartiles <- build_us_post_share_draws_quartiles(share_draws, parties, mrp_estimates)
	extended_frame <- build_us_post_extended_frame(prob_mat, frame_pred)
	stage_diagnostics <- compute_us_post_stage_diagnostics(sb_fits, parties)
	aggregate_counts <- compute_us_post_aggregate_counts(extended_frame)
	cd_party_point <- compute_us_post_cd_point(prob_mat, frame_pred, parties)
	cd_party_draws <- compute_us_post_cd_draws(pi_draws, frame_pred, parties)
	cd_party_quartiles <- compute_us_post_cd_quartiles(cd_party_draws, cd_party_point)
	share_draws_long <- build_us_post_share_draws_long(share_draws)

	list(
		point_estimates = mrp_estimates,
		quartile_table = quartile_table,
		share_draws_quartiles = share_draws_quartiles,
		extended_frame = extended_frame,
		stage_diagnostics = stage_diagnostics,
		aggregate_counts = aggregate_counts,
		share_draws = as_tibble(share_draws),
		share_draws_long = share_draws_long,
		cell_party_probabilities = as_tibble(prob_mat),
		stickbreaking_conditional_probs = as_tibble(pi_mat),
		cd_party_point = cd_party_point,
		cd_party_draws = cd_party_draws,
		cd_party_quartiles = cd_party_quartiles,
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
	write_csv(result$share_draws_quartiles, file.path(output_dir, "mrp_share_draws_quartiles.csv"))
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
		result$cd_party_point,
		file.path(output_dir, "mrp_cd_party_point_estimates.csv")
	)
	write_csv(
		result$cd_party_draws,
		file.path(output_dir, "mrp_cd_party_draws_long.csv")
	)
	write_csv(
		result$cd_party_quartiles,
		file.path(output_dir, "mrp_cd_party_quartiles.csv")
	)

	invisible(result)
}
