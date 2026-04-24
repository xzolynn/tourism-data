import pandas as pd

# Load the Excel file
file = '2025年统计表.xls'

# Read sheet '表3-3'
df = pd.read_excel(file, sheet_name='表3-3', header=None)

# Prefecture row
pref_row = df[df[1] == '調査項目'].iloc[0]

# Find columns for 石川県 and 福井県
ishikawa_col = pref_row[pref_row == '石川県'].index[0]
fukui_col = pref_row[pref_row == '福井県'].index[0]

print("Ishikawa column:", ishikawa_col)
print("Fukui column:", fukui_col)

# The data columns are ishikawa_col for responses, ishikawa_col+1 for consumption
# But for age, we need the number of responses for each age group.

# Age data starts from row 87
age_start = 87

# Age groups: rows 87 to 93 for males, 94 to ? for females
# But the data is number of responses in the prefecture columns

# For each age group, get the number for Ishikawa and Fukui

age_groups = ['15～19歳', '20～29歳', '30～39歳', '40～49歳', '50～59歳', '60～69歳', '70歳以上']

# Males are rows 87-93, females 95-101 or something

# Row 87: 15～19歳 male
# Row 88: 20～29歳 male
# etc.
# Row 94: female total
# Row 95: 15～19歳 female
# etc.

# To get total young, perhaps 15-29 or 20-29

# Let's collect data

ishikawa_data = {}
fukui_data = {}

for i, age in enumerate(age_groups):
    # Male
    male_row = age_start + i
    ishikawa_data[age + '_male'] = df.iloc[male_row, ishikawa_col]
    fukui_data[age + '_male'] = df.iloc[male_row, fukui_col]
    
    # Female
    female_row = age_start + 7 + i  # assuming 94 is female total, 95 is 15-19 female
    ishikawa_data[age + '_female'] = df.iloc[female_row, ishikawa_col]
    fukui_data[age + '_female'] = df.iloc[female_row, fukui_col]

print("Ishikawa age data:")
for k, v in ishikawa_data.items():
    print(f"{k}: {v}")

print("Fukui age data:")
for k, v in fukui_data.items():
    print(f"{k}: {v}")

# Calculate young tourists: 15-29
young_ishikawa = sum([ishikawa_data['15～19歳_male'], ishikawa_data['20～29歳_male'], ishikawa_data['15～19歳_female'], ishikawa_data['20～29歳_female']])
young_fukui = sum([fukui_data['15～19歳_male'], fukui_data['20～29歳_male'], fukui_data['15～19歳_female'], fukui_data['20～29歳_female']])

total_ishikawa = sum(ishikawa_data.values())
total_fukui = sum(fukui_data.values())

young_pct_ishikawa = young_ishikawa / total_ishikawa * 100 if total_ishikawa > 0 else 0
young_pct_fukui = young_fukui / total_fukui * 100 if total_fukui > 0 else 0

print(f"Ishikawa young (15-29) tourists: {young_ishikawa}/{total_ishikawa} = {young_pct_ishikawa:.2f}%")
print(f"Fukui young (15-29) tourists: {young_fukui}/{total_fukui} = {young_pct_fukui:.2f}%")
print("First 5 rows of xlsx:")
print(df_xlsx.head())