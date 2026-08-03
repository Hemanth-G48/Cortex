import type { Membership } from '../../services/api';

interface Props {
  membership: Membership | null;
}

/** Sidebar Membership widget (Phase 68): status badge + next-payment countdown. */
export const FhMembership = ({ membership }: Props) => {
  const status = membership?.membership_status ?? 'Active';
  const days = membership?.days_to_payment ?? null;

  return (
    <div className="fh-card">
      <div className="fh-card-title">Membership</div>
      <div className="fh-membership-row">
        <span>Status</span>
        <span className="fh-badge-active">
          <span aria-hidden="true">●</span> {status}
        </span>
      </div>
      <div className="fh-membership-row">
        <span>Next payment</span>
        <span>{membership?.next_payment_date ?? '—'}</span>
      </div>
      {days !== null && (
        <div className="fh-days-pay">
          Next payment is in <b>{days}</b> day{days === 1 ? '' : 's'}
        </div>
      )}
    </div>
  );
};
