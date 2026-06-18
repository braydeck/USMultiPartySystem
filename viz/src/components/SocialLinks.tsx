// Footer social links. Inline brand SVGs (simple-icons paths, 24×24 viewBox,
// fill=currentColor so they inherit text color + hover) to avoid an icon dependency.

interface Social {
  label: string;
  href: string;
  path: string;
}

const SOCIALS: Social[] = [
  {
    label: 'Contact',
    href: 'https://brayden-decker-contact.pages.dev/',
    path: 'M22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6zm-2 0-8 5L4 6h16zm0 12H4V8l8 5 8-5v10z',
  },
  {
    label: 'GitHub',
    href: 'https://github.com/braydeck/USMultiPartySystem',
    path: 'M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.014 2.898-.014 3.293 0 .322.216.694.825.576C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12',
  },
  {
    label: 'LinkedIn',
    href: 'https://www.linkedin.com/in/brayden-decker/',
    path: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z',
  },
  {
    label: 'Bluesky',
    href: 'https://bsky.app/profile/braydecker.bsky.social',
    path: 'M5.07 3.04c2.69 2.02 5.58 6.11 6.64 8.31.06.12.11.23.16.31.05-.08.1-.19.16-.31 1.06-2.2 3.95-6.29 6.64-8.31C20.42 1.59 23 .47 23 3.41c0 .59-.34 4.95-.54 5.66-.69 2.46-3.2 3.09-5.43 2.71 3.9.66 4.89 2.86 2.75 5.06-4.07 4.18-5.85-1.05-6.31-2.39-.08-.24-.12-.35-.12-.26 0-.09-.04-.02-.12.26-.46 1.34-2.24 6.57-6.31 2.39-2.14-2.2-1.15-4.4 2.75-5.06-2.23.38-4.74-.25-5.43-2.71C1.34 8.36 1 4 1 3.41 1 .47 3.58 1.59 5.07 3.04Z',
  },
  {
    label: 'Substack',
    href: 'https://braydendecker.substack.com/',
    path: 'M22.539 8.242H1.46V5.406h21.08v2.836zM1.46 10.812V24L12 18.11 22.54 24V10.812H1.46zM22.54 0H1.46v2.836h21.08V0z',
  },
];

export function SocialLinks() {
  return (
    <div className="flex items-center justify-center gap-5">
      {SOCIALS.map(s => (
        <a
          key={s.label}
          href={s.href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={s.label}
          title={s.label}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path d={s.path} />
          </svg>
        </a>
      ))}
    </div>
  );
}
