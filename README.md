# cssci-capstone-app


# Stratification frame
A stratification frame is a list of mutually exclusive and exhaustive cells. Each cell is described by a mutually exclusive set of combined characteristics (e.g. age, sex, education, income, municipality). Each cell is likewise associated with an N representing how many of a given cell exist in a population.

A sample cell might look like:

| Age   | Sex | Education   | Income  | Municipality | N   |
| ----- | --- | ----------- | ------- | ------------ | --- |
| 24-35 | M   | High school | 100,000 | Middelfart   | 355 |

## Denmark
In order to build the initial skeleton frame for all of Denmark (excluding Greenland and the Faroe Islands), we take three tables from Denmark's StatBank. 
1. [FOLK1D](http://www.statbank.dk/FOLK1D) - this table contains the "true N" by municipality, gender, and age. We take it as the true N, as it contains a column denoting citizenship (i.e. our voting population). We take the most recent available data (2026Q1).
2. [HFUDD11](https://www.statbank.dk/hfudd11) - this table contains educational attainment by municipality, gender, and age (ages 15-69). This is our relative N as it; a) contains older data (2024 latest), b) does not distinguish between citizens.
3. INCOME TABLE - NOT DONE. Take some table from the INKDP.

The FOLK1D (population table) is preprocessed by translating the columns, dropping regions to leave only the municipalities and recoding the age column to match the 5 year age groups in HFUDD11 (education table).

The education table is then preprocessed by dropping the granular education rows to match the granularity in the Danish National Election Survey.

### Combining Population Table with the Education Table
To combine the population table with the education table, we first calculate the proportion of a certain age, municipality and gender cell that has a certain education. For example, if there are 100 men aged 20-24 in the Bornholm municipality in our relative N, and 60 of them have a bachelor's degree, if our true N = 200, we will multiply to get: $true \ N = 200 * (\frac{60}{100}) = 120$. 

Given that our table goes up to 69 years old, there are 20+ years missing from the education data. To solve this, we take the HFUDD11 data going back to 2009, when it cuts off and we assume that the 65-69 year olds of 2019 did not get any higher education than they had 5 years ago. We thus apply this logic to 2019, 2014, and 2009 to get the education of age cohorts in 2024 aged 70-74, 75-79 and 80-84 respectively. We assume that 85+ year olds have the same education as 80-84 year olds. This results in an education distribution across age and municipalities that looks like the following. This means that the data for 3.3% of the population (those above 84) is synthesised in this manner.

![education across age and municipalities](denmark_data/data/images/education.png)

### Greenland and the Faroe Islands
Both of these places are 