/**
 * src/components/auth/AuthLayout.tsx
 */

import type { ReactNode } from 'react';
import { authStyles as s } from '../styles/auth';
import { ui } from '../styles/ui';

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className={s.page}>
      <Brand />
      <div className={s.card}>{children}</div>
    </div>
  );
}

function Brand() {
  return (
    <div className={s.brand}>
      <div className={ui.brandIcon}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2.5">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div>
        <div className={s.brandName}>SecureRAG</div>
        <div className={s.brandTagline}>Knowledge Assistant</div>
      </div>
    </div>
  );
}