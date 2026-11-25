// End labels for each policy domain's position scale on the Legislation tab: [0 end, 100 end].
// Item directions come from the data (lib/domainPosition.ts); only these labels are written by hand.
export const DOMAIN_POLES: Record<string, [string, string]> = {
  'Taxes & Economy': ['Tax and spend more', 'Tax and spend less'],
  'Immigration': ['More permissive', 'More restrictive'],
  'Police & Guns': ['More gun limits, less policing', 'Fewer gun limits, more policing'],
  'Abortion': ['Protect access', 'Restrict access'],
  'Civil Liberties': ['Fewer restrictions', 'More restrictions'],
  'Environment & Climate': ['More climate rules', 'More fossil fuels'],
  'Healthcare & Housing': ['Larger public role', 'Smaller public role'],
  'Budget': ['More social spending', 'Less social spending, more law enforcement'],
};
