'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CalendarDays,
  FileText,
  Search,
  Settings,
  Sparkles,
} from 'lucide-react';

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { name: 'New Meeting', href: '/new-briefing', icon: CalendarDays },
  { name: 'Briefing History', href: '/history', icon: FileText },
  { name: 'Research', href: '/research', icon: Search },
];

function isActive(pathname: string, href: string) {
  // a briefing page (/meetings/123) belongs to "Briefing History"
  return pathname === href || (href === '/history' && pathname.startsWith('/meetings'));
}

/** Compact top navigation shown on small screens (the fixed sidebar is desktop-only). */
export function MobileNav() {
  const pathname = usePathname();
  const items = [...navigation, { name: 'Settings', href: '/settings', icon: Settings }];

  return (
    <nav className="flex items-center gap-2 overflow-x-auto border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
      <div className="mr-2 flex shrink-0 items-center gap-2 font-bold text-slate-900">
        <Sparkles size={18} className="text-indigo-600" /> MeetWise
      </div>
      {items.map((item) => (
        <Link
          key={item.name}
          href={item.href}
          className={`shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium ${
            isActive(pathname, item.href) ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500'
          }`}
        >
          {item.name}
        </Link>
      ))}
    </nav>
  );
}

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 flex-col border-r border-slate-200 bg-white px-5 py-6 lg:flex">

      {/* Logo */}
      <div className="mb-10 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
          <Sparkles size={22} />
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            MeetWise<span className="text-indigo-600"> AI</span>
          </h1>
          <p className="text-sm text-slate-400">Meeting Intelligence</p>
        </div>
      </div>

      {/* Navigation */}
      <p className="mb-3 px-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Workspace
      </p>

      <nav className="space-y-2">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = isActive(pathname, item.href);

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-3 py-3 text-base font-medium transition ${
                active
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Icon size={20} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto">
        <Link
          href="/settings"
          className={`flex items-center gap-3 rounded-xl px-3 py-3 text-base hover:bg-slate-50 ${
            pathname === '/settings' ? 'bg-indigo-50 font-medium text-indigo-700' : 'text-slate-500'
          }`}
        >
          <Settings size={20} />
          Settings
        </Link>

        <div className="mt-5 rounded-2xl bg-indigo-50 p-4">
          <Sparkles className="mb-2 text-indigo-600" size={21} />

          <p className="text-base font-semibold text-slate-900">
            Meeting smarter starts here.
          </p>

          <p className="mt-1 text-sm leading-6 text-slate-500">
            Get prepared with AI-powered research and insights.
          </p>
        </div>
      </div>
    </aside>
  );
}
