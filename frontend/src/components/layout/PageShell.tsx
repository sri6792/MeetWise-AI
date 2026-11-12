'use client';

import type { ReactNode } from 'react';
import Sidebar, { MobileNav } from '@/components/layout/Sidebar';

/** Sidebar + content frame shared by every page (same look as the original dashboard). */
export default function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      <Sidebar />
      <MobileNav />
      <main className="min-h-screen p-4 sm:p-6 lg:ml-64 lg:p-8">{children}</main>
    </div>
  );
}
