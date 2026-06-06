import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb, to_hex
import io

data_str = """factor	tier_id	tier_label	type	SUM of score	SUM of seats_senate_irv	SUM of seats_house	Forecasted Senate
F1_security_order	0	Very Low	DSA	-1.3034	0	26	0
F1_security_order	0	Very Low	PRG	-1.26	0	8	0
F1_security_order	1	Low	LIB	-0.4623	0	100	0
F1_security_order	1	Low	SD	-0.4143	2	166	4
F1_security_order	1	Low	SD/LIB	-0.4378	4	0	8
F1_security_order	1	Low	SD/STY	-0.4247	10	0	20
F1_security_order	1	Low	STY	-0.446	0	160	0
F1_security_order	1	Low	STY/SD	-0.4301	5	0	10
F1_security_order	2	Medium	CON/SD	0.2357	6	0	12
F1_security_order	2	Medium	LIB/CTR	-0.1711	1	0	2
F1_security_order	2	Medium	REF	0.2023	1	125	2
F1_security_order	2	Medium	REF/STY	-0.0376	0	0	0
F1_security_order	2	Medium	SD/CON	0.1529	2	0	4
F1_security_order	2	Medium	SD/CTR	-0.1219	1	0	2
F1_security_order	2	Medium	STY/CON	0.0758	1	0	2
F1_security_order	2	Medium	STY/REF	-0.1543	2	0	4
F1_security_order	3	High	CON/CTR	0.5768	4	0	8
F1_security_order	3	High	CON/REF	0.5922	4	0	8
F1_security_order	3	High	CON/STY	0.2577	5	0	10
F1_security_order	3	High	CTR	0.2658	0	102	0
F1_security_order	3	High	NAT	0.7366	0	22	0
F1_security_order	4	Very High	CON	0.7674	2	164	4
F1_security_order	4	Very High	CON/NAT	0.7523	1	0	2
F2_electoral_skepticism	0	Very Low	CTR	-0.8166	0	102	0
F2_electoral_skepticism	0	Very Low	LIB/CTR	-0.7729	1	0	2
F2_electoral_skepticism	1	Low	CON/CTR	-0.3248	4	0	8
F2_electoral_skepticism	1	Low	LIB	-0.7437	0	100	0
F2_electoral_skepticism	1	Low	PRG	-0.6338	0	8	0
F2_electoral_skepticism	1	Low	SD/CTR	-0.3694	1	0	2
F2_electoral_skepticism	1	Low	SD/LIB	-0.3808	4	0	8
F2_electoral_skepticism	2	Medium	CON	-0.0235	2	164	4
F2_electoral_skepticism	2	Medium	CON/NAT	0.1976	1	0	2
F2_electoral_skepticism	2	Medium	CON/REF	0.2192	4	0	8
F2_electoral_skepticism	2	Medium	CON/SD	-0.0274	6	0	12
F2_electoral_skepticism	2	Medium	SD	-0.0321	2	166	4
F2_electoral_skepticism	2	Medium	SD/CON	-0.028	2	0	4
F2_electoral_skepticism	2	Medium	SD/STY	0.1956	10	0	20
F2_electoral_skepticism	3	High	CON/STY	0.2627	5	0	10
F2_electoral_skepticism	3	High	DSA	0.504	0	26	0
F2_electoral_skepticism	3	High	NAT	0.4278	0	22	0
F2_electoral_skepticism	3	High	REF/STY	0.7218	0	0	0
F2_electoral_skepticism	3	High	STY	0.6579	0	160	0
F2_electoral_skepticism	3	High	STY/CON	0.3649	1	0	2
F2_electoral_skepticism	3	High	STY/REF	0.7035	2	0	4
F2_electoral_skepticism	3	High	STY/SD	0.3129	5	0	10
F2_electoral_skepticism	4	Very High	REF	0.7593	1	125	2
F3_government_distrust	2	Medium	CON	0.1108	2	164	4
F3_government_distrust	2	Medium	CON/CTR	0.0024	4	0	8
F3_government_distrust	2	Medium	CON/NAT	-0.0453	1	0	2
F3_government_distrust	2	Medium	CON/REF	0.0126	4	0	8
F3_government_distrust	2	Medium	CON/SD	0.1021	6	0	12
F3_government_distrust	2	Medium	CON/STY	0.1202	5	0	10
F3_government_distrust	2	Medium	CTR	-0.1744	0	102	0
F3_government_distrust	2	Medium	DSA	0.0761	0	26	0
F3_government_distrust	2	Medium	LIB	-0.0862	0	100	0
F3_government_distrust	2	Medium	LIB/CTR	-0.1215	1	0	2
F3_government_distrust	2	Medium	NAT	-0.2078	0	22	0
F3_government_distrust	2	Medium	PRG	-0.2057	0	8	0
F3_government_distrust	2	Medium	REF	-0.2061	1	125	2
F3_government_distrust	2	Medium	REF/STY	-0.0805	0	0	0
F3_government_distrust	2	Medium	SD	0.0915	2	166	4
F3_government_distrust	2	Medium	SD/CON	0.1007	2	0	4
F3_government_distrust	2	Medium	SD/CTR	-0.0228	1	0	2
F3_government_distrust	2	Medium	SD/LIB	0.0044	4	0	8
F3_government_distrust	2	Medium	SD/STY	0.1053	10	0	20
F3_government_distrust	2	Medium	STY	0.1333	0	160	0
F3_government_distrust	2	Medium	STY/CON	0.1236	1	0	2
F3_government_distrust	2	Medium	STY/REF	-0.0194	2	0	4
F3_government_distrust	2	Medium	STY/SD	0.1124	5	0	10
F4_religious_traditionalism	1	Low	DSA	-0.3869	0	26	0
F4_religious_traditionalism	1	Low	LIB	-0.323	0	100	0
F4_religious_traditionalism	1	Low	PRG	-0.3869	0	8	0
F4_religious_traditionalism	1	Low	SD	-0.3447	2	166	4
F4_religious_traditionalism	1	Low	SD/LIB	-0.3341	4	0	8
F4_religious_traditionalism	2	Medium	CON	0.2186	2	164	4
F4_religious_traditionalism	2	Medium	CON/CTR	0.1848	4	0	8
F4_religious_traditionalism	2	Medium	CON/REF	0.1964	4	0	8
F4_religious_traditionalism	2	Medium	CON/SD	-0.0349	6	0	12
F4_religious_traditionalism	2	Medium	CON/STY	0.1959	5	0	10
F4_religious_traditionalism	2	Medium	CTR	0.1296	0	102	0
F4_religious_traditionalism	2	Medium	LIB/CTR	-0.142	1	0	2
F4_religious_traditionalism	2	Medium	REF	0.147	1	125	2
F4_religious_traditionalism	2	Medium	REF/STY	0.1535	0	0	0
F4_religious_traditionalism	2	Medium	SD/CON	-0.0743	2	0	4
F4_religious_traditionalism	2	Medium	SD/CTR	-0.1408	1	0	2
F4_religious_traditionalism	2	Medium	SD/STY	-0.1767	10	0	20
F4_religious_traditionalism	2	Medium	STY	0.1645	0	160	0
F4_religious_traditionalism	2	Medium	STY/CON	0.1878	1	0	2
F4_religious_traditionalism	2	Medium	STY/REF	0.1566	2	0	4
F4_religious_traditionalism	2	Medium	STY/SD	-0.0901	5	0	10
F4_religious_traditionalism	3	High	CON/NAT	0.3356	1	0	2
F4_religious_traditionalism	3	High	NAT	0.4573	0	22	0
F5_populist_conservatism	0	Very Low	DSA	-0.874	0	26	0
F5_populist_conservatism	0	Very Low	LIB	-0.9496	0	100	0
F5_populist_conservatism	0	Very Low	PRG	-0.99	0	8	0
F5_populist_conservatism	0	Very Low	SD/LIB	-0.7529	4	0	8
F5_populist_conservatism	1	Low	LIB/CTR	-0.5543	1	0	2
F5_populist_conservatism	1	Low	SD	-0.564	2	166	4
F5_populist_conservatism	1	Low	SD/CTR	-0.3048	1	0	2
F5_populist_conservatism	1	Low	SD/STY	-0.3984	10	0	20
F5_populist_conservatism	1	Low	STY/SD	-0.3132	5	0	10
F5_populist_conservatism	2	Medium	CON/SD	-0.0105	6	0	12
F5_populist_conservatism	2	Medium	CON/STY	0.2304	5	0	10
F5_populist_conservatism	2	Medium	CTR	0.0387	0	102	0
F5_populist_conservatism	2	Medium	SD/CON	-0.0809	2	0	4
F5_populist_conservatism	2	Medium	STY	-0.0623	0	160	0
F5_populist_conservatism	2	Medium	STY/CON	0.1547	1	0	2
F5_populist_conservatism	3	High	CON	0.4424	2	164	4
F5_populist_conservatism	3	High	CON/CTR	0.289	4	0	8
F5_populist_conservatism	3	High	CON/REF	0.6122	4	0	8
F5_populist_conservatism	3	High	REF/STY	0.6008	0	0	0
F5_populist_conservatism	3	High	STY/REF	0.4114	2	0	4
F5_populist_conservatism	4	Very High	CON/NAT	0.9656	1	0	2
F5_populist_conservatism	4	Very High	NAT	1.5101	0	22	0
F5_populist_conservatism	4	Very High	REF	0.9903	1	125	2"""

df = pd.read_csv(io.StringIO(data_str), sep='\t')
for col in ['tier_id', 'SUM of score', 'SUM of seats_senate_irv', 'SUM of seats_house', 'Forecasted Senate']:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if col != 'SUM of score': df[col] = df[col].astype(int)

# Highly distinct, saturated categorical colors
colors_base = {
    'DSA': '#E6194B',  # Magenta/Pinkish-Purple
    'PRG': '#F032E6',  # Hot Pink
    'LIB': '#911EB4',  # Purple
    'SD':  '#4363D8',  # Solid Blue
    'CTR': '#A9A9A9',  # Mid Grey
    'STY': '#3CB44B',  # Green
    'REF': '#F58231',  # Orange
    'CON': '#9A6324',  # Red
    'NAT': '#000000'   # Black
}

def get_party_color(type_str):
    type_str = str(type_str).strip()
    if pd.isna(type_str) or type_str == 'nan': return 'white'
    
    if '/' in type_str:
        parts = type_str.split('/')
        rgbs = [np.array(to_rgb(colors_base.get(p.strip(), 'white'))) for p in parts]
        if rgbs: return to_hex(np.mean(rgbs, axis=0))
    return colors_base.get(type_str, 'white')

def get_hemicycle_coords(n_seats):
    if n_seats == 0: return np.array([]), np.array([])
    nrows = max(1, int(np.sqrt(n_seats) * 0.4))
    radii = np.linspace(1, 2, nrows)
    ideal_dist = (n_seats * radii) / radii.sum()
    seats_per_row = ideal_dist.round().astype(int)
    
    diff = n_seats - seats_per_row.sum()
    while diff != 0:
        idx = len(seats_per_row) - 1
        adj = 1 if diff > 0 else -1
        seats_per_row[idx] += adj
        diff -= adj
        idx = (idx - 1) % len(seats_per_row)
    
    all_x, all_y, all_angles = [], [], []
    for i, r in enumerate(radii):
        n = seats_per_row[i]
        if n == 0: continue
        theta = np.linspace(np.pi, 0, n)
        all_x.extend(r * np.cos(theta))
        all_y.extend(r * np.sin(theta))
        all_angles.extend(theta)
    
    coords = np.column_stack((all_x, all_y, all_angles))
    sorted_coords = coords[np.argsort(coords[:, 2])[::-1]]
    return sorted_coords[:, 0], sorted_coords[:, 1]

def plot_chart(f_df, col_name, factor_label, chart_type, factor_id):
    tier_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']
    bg_color = '#f5f5f5' # Light grey background
    
    colors_list = []
    legend_dict = {}
    
    # STRICT SORT BY SCORE: Guarantees Left-To-Right mapping irrespective of color assigned
    f_df = f_df.sort_values(by=['tier_id', 'SUM of score'], ascending=[True, True])
    
    for tier in tier_order:
        t_df = f_df[f_df['tier_label'] == tier].sort_values(by='SUM of score', ascending=True)
        for _, row in t_df.iterrows():
            count = int(row[col_name])
            if count > 0:
                color = get_party_color(row['type'])
                colors_list.extend([color] * count)
                legend_dict[row['type']] = color
    
    n_seats = len(colors_list)
    if n_seats == 0: return

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    plt.subplots_adjust(top=0.85, bottom=0.2)
    
    x, y = get_hemicycle_coords(n_seats)
    marker_size = 40 if n_seats < 200 else 10
    
    # Render with dark edges for visibility
    ax.scatter(x, y, c=colors_list, s=marker_size, marker='s', edgecolors='#555555', linewidths=0.5)
    
    # 1. GEOMETRY FIX: Force aspect ratio to identical scale (prevents squishing)
    ax.set_aspect('equal', adjustable='box')
    
    # 2. BOUNDARY FIX: Give symmetrical limits so text fits cleanly
    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(-0.1, 2.8)
    
    cum_seats = 0
    R_inner, R_outer, label_R = 0.9, 2.1, 2.3
    for tier in tier_order:
        tier_sum = f_df[f_df['tier_label'] == tier][col_name].sum()
        if tier_sum > 0:
            start_idx = cum_seats
            end_idx = cum_seats + tier_sum
            
            start_a = np.arctan2(y[start_idx], x[start_idx])
            last_a = np.arctan2(y[end_idx-1], x[end_idx-1])
            
            if tier != 'Very High' and end_idx < n_seats:
                next_a = np.arctan2(y[end_idx], x[end_idx])
                div_a = np.mean([last_a, next_a])
                ax.plot([R_inner*np.cos(div_a), R_outer*np.cos(div_a)], 
                        [R_inner*np.sin(div_a), R_outer*np.sin(div_a)], color='black', lw=1.5, alpha=0.5)
            
            mid_a = np.mean([start_a, last_a])
            rot = np.degrees(mid_a) - 90
            ax.text(label_R*np.cos(mid_a), label_R*np.sin(mid_a), tier, 
                    ha='center', va='center', rotation=rot, fontweight='bold', fontsize=12)
            
            cum_seats += tier_sum

    ax.set_title(f"{chart_type}: {factor_label}\n(Total Seats: {n_seats})", fontsize=18, fontweight='bold', pad=15)
    ax.axis('off')

    # Re-sort legend just for alphabetical/clean rendering
    sorted_legend = sorted(legend_dict.items())
    legend_elems = [plt.Line2D([0], [0], marker='s', color=bg_color, label=k, 
                    markerfacecolor=v, markeredgecolor='#555555', markersize=10) for k, v in sorted_legend]
    
    leg = fig.legend(handles=legend_elems, loc='lower center', ncol=min(len(sorted_legend), 5), 
                     title="Discrete Party Coalitions", facecolor=bg_color, frameon=False)
    
    filename = f"{chart_type.lower().replace(' ', '_')}_{factor_id}_categorical.png"
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    plt.close()
    return filename

generated_files = []
factors = df['factor'].unique()
for f in factors:
    factor_clean = f.split('_', 1)[1].replace('_', ' ').title()
    h_file = plot_chart(df[df['factor'] == f], 'SUM of seats_house', factor_clean, "House Seats", f)
    s_file = plot_chart(df[df['factor'] == f], 'Forecasted Senate', factor_clean, "Projected Senate", f)
    if h_file: generated_files.append(h_file)
    if s_file: generated_files.append(s_file)

print(generated_files)