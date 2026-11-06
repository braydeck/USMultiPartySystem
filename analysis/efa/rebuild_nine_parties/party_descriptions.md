# Party descriptions: the nine

Draft 2026-11-05 for the researcher to edit. These replace `PARTY_TAGLINES` and the paragraph descriptions in
`viz/src/constants/parties.ts` once final. Each party has a **Name**, a **Tagline** (one line) and a
**Paragraph**, the interpretive reading. Under each, the evidence behind the reading:

- **Apart**: positions where the party differs from each of its three nearest neighbors (four-factor centroid
  distance) by at least 15 points.
- **Cohesive**: positions at least 70% of the party shares.
- **Deviant / mainstream**: at least 25 points from everyone, or within 10 points of everyone on an item the
  parties split on.
- **Cohesive and mainstream**: both at once, a national consensus the party holds while other parties break from it.
  These are signature positions too.

The full tables are in `description_evidence.md` (written by `description_evidence.py`; CES 2024, weighted). The
evidence blocks are not app copy. Parties run in left-right order (Economic Conservatism).

---

## OAO (cluster G, 7.5%)

**Name:** Order and Opportunity

**Tagline:** Spends on health care, schools, and police alike, and trusts government the most

**Paragraph:** The urban Democratic base. Its members want government to do more of everything, policing included:
they back Medicaid expansion, student-debt relief, and more state health spending at near-unanimity, along with
more police and border patrols. They trust the federal and state governments more than any other party. On
culture they sit near the national average, and three in ten attend church weekly. Older city residents, the
highest Black and Catholic shares of any party, and the fewest independents.

> Apart from CUP, STY, LBR: more state spending on law enforcement 88% (highest of nine; CUP 60, STY 37, LBR 16);
> slavery and discrimination make it hard for Black Americans to rise 69% (CUP 49, STY 50, LBR 91).
> Cohesive: state health spending 100%, Medicaid 99%, border patrols 96%, student debt 95%, taxes on $400k+ 90%,
> more police 68%. Little or no trust in the federal government 35%, state government 29% (both lowest).
> Cohesive and mainstream: 2024 local election fair 84%, same-sex marriage 73%, contraception 72%, abortion-access
> protections 72%, troops to protect allies 74%; move police funding to other services 17%.
> Mainstream: parental consent on pronouns 75%, vouchers 61%, extend the 2017 tax cuts 60%, more fossil fuels 54%.
> Weekly church attendance 30%, born-again 43%. Black 31%, Catholic 22%, city 39% (all highest), independent 22%
> (lowest), median age 62.

## PRG (cluster H, 6.1%)

**Name:** Progressive

**Tagline:** The professional left: progressive across the board, the most politically active, and pro-Ukraine

**Paragraph:** The left's professional and activist class. Progressive on every domain at near-unanimity, and the
party most committed to Ukraine. It is also the most politically active party: nearly half gave money to a
campaign in the past year, and it has the highest verified turnout. It accepts border patrols and trusts elections. The most college-educated, highest-income, and most invested party.

> Apart from LBR, DSA, CUP: arms to Ukraine 82%, sanctions on Russia 87%, non-combat advisors 60%, donated to a
> campaign 49%, verified 2024 turnout 85% (all highest of nine).
> Cohesive: always allow abortion 98%, taxes on $400k+ 98%, renewable standard 99%, assault-weapons ban 97%,
> legal status 95%; tax cuts 7%, vouchers 3%.
> Mainstream: little or no trust in the federal government 54%, state government 38%.
> Bachelor's or more 59%, family income $100k+ 41%, owns stock 59%, follows public affairs 78%, union member 10%
> (all highest). Democrat 76%.

## DSA (cluster I, 3.3%)

**Name:** Democratic Socialists

**Tagline:** Against police, border enforcement, and surveillance; the youngest and most secular party

**Paragraph:** The anti-state left. Its members are unanimous against police and border enforcement, distrust the
federal government, and oppose state controls on speech and the internet. It has the most support of any party
for non-combat aid to Gaza. The youngest party, and the most secular, LGBT, and unmarried. Mostly
renters, and the most likely to have protested in the past year.

> Apart from LBR, PRG, STY: move police funding to other services 100%, more border patrols 1%, more state spending
> on law enforcement 0% (all most extreme of nine); little or no trust in the federal government 86%; ban TikTok
> 11%, age verification for adult sites 37%, troops to destroy a terrorist camp 19% (all lowest); non-combat
> support for Gaza 43% (highest).
> Cohesive: student debt 100%, Medicaid 100%, always allow abortion 100%, legal status 99%, state welfare spending
> 94%.
> Mainstream: elections in the U.S. are fair 55%, 2024 local election fair 79%.
> Median age 37, under 30 45%, LGBT 46%, atheist or agnostic 50%, never married 55%, protested in the past year
> 18% (all highest); owns home 50% (lowest).

## LBR (cluster E, 11.7%)

**Name:** Labor

**Tagline:** Progressive on rights, climate, and taxes; three in ten cross over on tax cuts and vouchers

**Paragraph:** The left's rank and file. It is for abortion rights, a path to legal status, clean-energy rules,
Medicaid expansion, and higher taxes on top earners, each at roughly nine in ten. About three in ten members back
the 2017 tax cuts, school vouchers, and limits on gender medicine for minors, and just over half want more state
welfare spending. It trusts government and elections at about the national average. The most suburban party.

> Apart from PRG, DSA, STY: extend the 2017 tax cuts 33% (PRG 7, DSA 14, STY 75); vouchers 30%; prevent gender
> transition for minors 29%; the ruling against race in admissions 35%; more state welfare spending 55% (PRG 81,
> DSA 94, STY 38).
> Cohesive: Medicaid 98%, always allow abortion 96%, renewable standard 96%, taxes on $400k+ 92%, legal status 89%.
> Mainstream: elections fair 64%, little or no trust in the federal government 60%, follows public affairs 53%.
> Suburb 46% (highest), bachelor's or more 46%, under 30 31%, atheist or agnostic 32%, median age 53.

## STY (cluster D, 22.1%)

**Name:** Solidarity

**Tagline:** The working-class middle: economically left, culturally traditional, and least engaged in politics

**Paragraph:** The working-class middle, and the largest party. Its members agree on the country's consensus
positions: seven in ten or more back border patrols, parental consent on pronouns, higher taxes on top earners,
infrastructure and mental-health spending, and age checks on adult websites, each within ten points of the national
figure. Beyond that consensus it leans left on economic help (student-debt relief, Medicaid) and right on school
vouchers and the 2017 tax cuts. It is also the party furthest from politics: one in five follows public affairs and
31% voted in 2024 by the voter file, both the lowest of any party, and few back arms or aid for Ukraine (16% and
40%). Majority non-white; the lowest-income, most female, and most Southern party, with the most children at home.

> Apart from OAO, LBR, CUP: follows public affairs 20%, verified 2024 turnout 31% (both lowest of nine); arms to
> Ukraine 16%, Ukraine humanitarian aid 40%, sanctions on Russia 20%, Gaza peace settlement 36%; 2024 local
> election fair 59%; repeal the ACA 39%.
> Cohesive and mainstream: mental health and school safety 90%, age verification 82%, $150B on infrastructure 75%,
> taxes on $400k+ 73%, border patrols 72%, parental consent 71%; racial problems are rare 21%, owns a gun 18%.
> Cohesive beyond the national figure: Medicaid 92%, student debt 85%, tax cuts 75%, vouchers 73%.
> Mainstream (60 items): ACA repeal 39%, more fossil fuels 58%, same-sex marriage 64%, abortion-access protections
> 64%, the wall 50%.
> White 48%, family income under $50k 56%, high school or less 49%, women 60%, South 45%, children at home 33%,
> Hispanic 14% (each the most or least of nine); Black 24%, median age 48.

## CUP (cluster F, 10.8%)

**Name:** Civic Union

**Tagline:** Socially liberal and pro-police; funds public services and resists aid paid to individuals

**Paragraph:** The fiscally cautious center. Socially liberal on abortion, same-sex marriage, and assault
weapons, pro-police, and trusting of elections. It funds shared public services: nine in ten back infrastructure
and mental-health and school-safety spending, seven in ten want more state spending on health care, schools, and
roads, and eight in ten back Medicaid expansion and higher taxes on top earners. It resists aid paid to
individuals: 37% back student-debt relief, 20% want more state welfare spending, and a majority would add work
requirements to Medicaid. It has the most self-described moderates of any party.

> Apart from OAO, STY, LBR: student-debt relief 37% (OAO 95, STY 85, LBR 94); more state welfare spending 20%;
> parental consent on pronouns 48%; abortion only in rape, incest or danger 39%; Roe overruled correctly 25%;
> religion important 51%.
> Cohesive: more border patrols 93%, always allow abortion 82%, same-sex marriage 82%, elections fair 82%,
> Medicaid 81%, assault-weapons ban 79%; vouchers 26%.
> Spending: $150B a year on infrastructure 89%, mental health and school safety 96%, state health 71%, education 70%,
> roads 69%; Medicaid 81%, taxes on $400k+ 80%, corporate tax 76%; Medicaid work requirement 56%.
> Cohesive and mainstream: mental health and school safety 96%, $150B on infrastructure 89%, Medicaid 81%,
> Dreamers 79%, age verification 77%, affordable-housing credits 72%, state health 71% and education 70% spending.
> Mainstream (48 items): more police 62%, state law-enforcement spending 60%, deny asylum 67%, affordable-housing
> credits 72%.
> Moderate 56% (highest), Asian 7% (highest), median age 62, owns home 73%.

## CON (cluster A, 17.6%)

**Name:** Conservative

**Tagline:** United on borders, police, energy, and tax cuts; split on abortion, guns, and climate

**Paragraph:** The mainstream right. Its members agree on order and low taxes: the wall, more police, border
patrols, fossil fuels, and the 2017 tax cuts. On abortion, guns, climate, immigration status, and the Affordable Care
Act they split, with a third to a half taking the liberal position. On spending and trust in elections it sits at
the national average. The most Republican-identifying party.

> Apart from NAT, CUP, STY: always allow abortion 36% (NAT 10, CUP 82, STY 66); assault-weapons ban 40%; EPA CO2
> rules 38%; legal status 36%; Dreamers 53%; taxes on $400k+ 54%; repeal the ACA 56% (NAT 91, CUP 11, STY 39);
> easier concealed carry 55%; same-sex marriage 48%.
> Cohesive: border patrols 98%, the wall 93%, more fossil fuels 90%, parental consent 89%, more police 84%, state
> law-enforcement spending 83%, tax cuts 81%.
> Cohesive and mainstream: age verification 89%, mental health and school safety 87%, 2024 local election fair
> 78%, $150B on infrastructure 77%.
> Mainstream (31 items): elections fair 65%, infrastructure 77%, mental health and school safety 87%, Medicaid 70%,
> state education spending 59%.
> Republican 64% (highest), conservative 65%, white 82%, owns home 78%, median age 62.

## NAT (cluster B, 18.0%)

**Name:** Nationalist

**Tagline:** Conservative on every issue at near-unanimity, and the most politically engaged right

**Paragraph:** The conservative core. It takes the right-hand position on nearly every item at near-unanimity, and
it is the party most set against the health-care safety net: nine in ten would repeal the Affordable Care Act, and
fewer than one in five want more state health spending. It takes the most resentful position of any party on all
nine racial and gender resentment items. It is the party most attached to property and arms: older, white, rural
homeowners, stockholders, and gun owners. It follows politics closely and votes almost without
exception.

> Apart from CON, POP, STY: repeal the ACA 91% (CON 56, POP 54, STY 39); renewable standard 10%; racial problems are
> rare 69%; easier concealed carry 85%; assault-weapons ban 9%; corporate tax increase 8%; taxes on $400k+ 13%;
> arms to Israel 65%; owns a gun 55% (each the most or least of nine); follows public affairs 73% (second to PRG).
> Cohesive: the wall 99%, fossil fuels 99%, parental consent 99%, Roe overruled correctly 99%, tax cuts 96%; state
> health spending 18%, state welfare spending 2%, student debt 1%.
> Deviant: women are too easily offended 67%, minorities should work their way up without favors 90% (both highest).
> Self-reported 2024 turnout 98%, veteran 19%, conservative 83%, white 84%, rural 29%, owns home 85% (all highest);
> under 30 8%, LGBT 3% (both lowest); owns stock 57% (highest on the right).

## POP (cluster C, 2.9%)

**Name:** Populist

**Tagline:** Distrusts elections and government, opposes public spending of every kind, and wants out of foreign wars

**Paragraph:** The disaffected right. Distrust defines it: it has the least faith in elections and state government
of any party. It opposes spending on roads, police, and welfare alike, and it wants the U.S. out of Ukraine and Gaza.
On abortion, the wall, and guns it sits at the national average. Younger, the most independent and religiously
unaffiliated party, and the most often out of work. Three in ten follow public affairs, and a third voted in 2024 by
the voter file.

> Apart from STY, NAT, CON: elections in the U.S. are fair 28%, 2024 local election fair 39%, little or no trust in
> state government 78%; state infrastructure spending 20%, $150B a year on infrastructure 38%; stay out of Ukraine
> 55%, stay out of Israel and Gaza 55%, troops for none of these reasons 43% (each the most or least of nine);
> state law-enforcement spending 11% (NAT 84, CON 83); born-again 23%.
> Cohesive: little or no trust in the federal government 88% (highest); state welfare spending 11%, state health
> spending 18%.
> Mainstream (26 items): always allow abortion 59%, the wall 53%, owns a gun 31%, conservative 38%, Republican 31%.
> Independent 47%, religion "nothing in particular" 32%, unemployed or laid off 16% (all highest); median age 46,
> follows public affairs 29%, verified 2024 turnout 35%.
