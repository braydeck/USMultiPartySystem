import type { AnchorHTMLAttributes } from 'react';

interface Props extends AnchorHTMLAttributes<HTMLAnchorElement> {
  href: string;
  onNavigate: () => void;
}

/**
 * A real anchor so the browser offers "open in new tab" (right-click, middle-click,
 * ⌘/Ctrl-click). Plain left-clicks are intercepted for in-app navigation; modified
 * clicks fall through to the browser's default handling.
 */
export function StateLink({ href, onNavigate, onClick, children, ...rest }: Props) {
  return (
    <a
      href={href}
      onClick={e => {
        onClick?.(e);
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        onNavigate();
      }}
      {...rest}
    >
      {children}
    </a>
  );
}
