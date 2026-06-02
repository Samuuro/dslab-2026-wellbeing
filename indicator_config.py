"""
indicator_config.py
====================
Single source of truth for how each OECD "Current well-being" indicator is treated
in the "Beyond the Average" project.

Decisions validated jointly with the team (checked against real 2022 country values
where direction was not obvious from the name).

DIRECTION:
  +1  higher value = better well-being
  -1  lower value  = better well-being (reversed during normalization)

ROLE:
  "level"      -> feeds the composite AVERAGE well-being index
  "gender_gap" -> already a gap measure; feeds the INEQUALITY index (gender axis)
  "vertical"   -> top/bottom ratio; feeds the INEQUALITY index (vertical axis), kept separate
"""

# --- Indicators feeding the AVERAGE well-being index (level indicators) ---
# direction validated; "Housing affordability" CORRECTED to +1 after checking real values
# (it is the % of disposable income REMAINING; higher = more affordable = better).
LEVEL_INDICATORS = {
    'Access to green space': +1,
    'Adult literacy skills': +1,
    'Adult numeracy skills': +1,
    'Adults with low numeracy skills': -1,
    'Average annual gross earnings': +1,
    'Deaths from suicide, alcohol, drugs': -1,
    'Difficulty making ends meet': -1,            # verified: Greece 68% (worst) vs Luxembourg 6% (best)
    'Employment rate': +1,
    'Equivalised liquid financial assets below three months of the annual national relative income poverty line': -1,
    'Exposed to air pollution': -1,
    'Exposure to extreme temperature': -1,
    'Feeling lonely': -1,
    'Feeling safe at night': +1,
    'Feelings of physical pain': -1,
    'Full-time employees earning less than two-thirds of gross median earnings': -1,
    'Having a say in government': +1,
    'Homicides': -1,
    'Household disposable income below the relative income poverty line': -1,
    'Households and NPISHs net adjusted disposable income per capita': +1,
    'Households living in overcrowded conditions': -1,
    'Households with internet access at home': +1,
    'Housing affordability': +1,                  # CORRECTED (was -1): higher = more income remains = better
    'Housing cost overburden': -1,                # verified: Colombia 49% (worst) vs Czechia 3% (best)
    'Inability to keep home adequately warm': -1,
    'Job satisfaction': +1,
    'Job strain': -1,                             # note: total-population value often missing in 2022
    'Labour market insecurity': -1,              # note: total-population value often missing in 2022
    'Life expectancy at birth': +1,
    'Life satisfaction': +1,
    'Life satisfaction score less than 5': -1,
    'Long hours in paid work': -1,
    'Long unpaid working hours': -1,
    'Long-term unemployment rate': -1,
    'Median net wealth': +1,                      # sparse coverage; level of wealth, not its distribution
    'Negative affect balance': -1,                # verified: Türkiye 38% (worst) vs Switzerland 6% (best)
    'Not feeling safe at night': -1,
    'Not having a say in government': -1,
    'Perceived health as negative': -1,
    'Perceived health as positive': +1,
    'Road deaths': -1,
    'Satisfaction with personal relationships': +1,
    'Satisfaction with personal relationships score less than 5': -1,
    'Satisfaction with time use': +1,
    'Satisfaction with time use score less than 5': -1,
    'Self-reported depression': -1,
    'Social support': +1,
    'Student mathematics skills': +1,
    'Student reading skills': +1,
    'Student science skills': +1,
    'Students with low skills in reading, mathematics and science': -1,
    'Time off': +1,                               # leisure hours/day; higher = better for our purposes
    'Time spent in social interactions': +1,
    'Voter turnout': +1,
    'Youth not in employment, education or training': -1,
}

# --- Indicators that are themselves GAP measures -> INEQUALITY index (gender axis) ---
# (moved out of the average per team decision)
GENDER_GAP_INDICATORS = {
    'Gender wage gap': -1,            # smaller gap = better
    'Gender gap in working hours': -1,
}

# --- Top/bottom ratio indicators -> INEQUALITY index (vertical axis), kept SEPARATE ---
# These are ratios (top decile/quintile vs bottom). Higher ratio = more vertical inequality = worse.
VERTICAL_INEQUALITY_INDICATORS = [
    'Top adult literacy scores decile',
    'Top adult numeracy scores decile',
    'Top average household disposable income quintile',
    'Top earnings of full-time employees decile',
    'Top life satisfaction scores quintile',
    'Top mathematics scores decile',
    'Top personal relationship satisfaction scores quintile',
    'Top reading scores decile',
    'Top satisfaction with time use quintile',
    'Top science scores decile',
    'Top wealthiest households decile',
]

# Horizontal gaps we COMPUTE ourselves from the decomposed slices (age / sex / education),
# using LEVEL_INDICATORS that are available broken down by those dimensions.
HORIZONTAL_AXES = {
    'age':       ('Young', 'Old'),
    'sex':       ('Female', 'Male'),
    'education': ('Tertiary education', 'Primary education'),
}

# Geographic grouping for the narrative lens (Northern/Southern/Eastern/Western Europe + Other)
GEO_GROUPS = {
    'Northern': ['Denmark', 'Finland', 'Iceland', 'Norway', 'Sweden'],
    'Western':  ['Austria', 'Belgium', 'France', 'Germany', 'Ireland', 'Luxembourg',
                 'Netherlands', 'Switzerland', 'United Kingdom'],
    'Southern': ['Greece', 'Italy', 'Portugal', 'Spain', 'Slovenia', 'Croatia'],
    'Eastern':  ['Bulgaria', 'Czechia', 'Estonia', 'Hungary', 'Latvia', 'Lithuania',
                 'Poland', 'Romania', 'Slovak Republic'],
    # 'Other' (non-European / Anglosphere overseas) handled as a residual category in code
}

if __name__ == '__main__':
    n_level = len(LEVEL_INDICATORS)
    n_pos = sum(1 for v in LEVEL_INDICATORS.values() if v == 1)
    n_neg = sum(1 for v in LEVEL_INDICATORS.values() if v == -1)
    print(f"Level indicators: {n_level} (+1: {n_pos}, -1: {n_neg})")
    print(f"Gender-gap indicators: {len(GENDER_GAP_INDICATORS)}")
    print(f"Vertical-inequality indicators: {len(VERTICAL_INEQUALITY_INDICATORS)}")
    print(f"Horizontal axes: {list(HORIZONTAL_AXES)}")
