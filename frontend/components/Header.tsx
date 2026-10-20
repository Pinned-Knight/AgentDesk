"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import HealthPill from "./HealthPill";

const NAV = [
  { href: "/", label: "Chat" },
  { href: "/dashboard", label: "Dashboard" },
];

export default function Header() {
  const pathname = usePathname() ?? "/";

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link href="/" className="brand" aria-label="AgentDesk home">
          <span className="logo" aria-hidden="true" />
          <span className="brand__name">AgentDesk</span>
        </Link>
        <nav className="nav" aria-label="Primary">
          {NAV.map(({ href, label }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`nav__link${active ? " is-active" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                {label}
              </Link>
            );
          })}
        </nav>
        <HealthPill />
      </div>
    </header>
  );
}
