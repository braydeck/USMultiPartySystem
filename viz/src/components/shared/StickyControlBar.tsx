interface Props {
  children: React.ReactNode;
}

export function StickyControlBar({ children }: Props) {
  return (
    <div className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-border/50 -mx-4 px-4 py-2 flex flex-wrap items-center gap-4">
      {children}
    </div>
  );
}
