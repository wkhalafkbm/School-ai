export interface Applicant {
  id: string;
  name: string;
  nationality: string;
  admission_term: string;
  program_name: string;
  program_interest: string;
  degree_level: string;
  sponsorship_status: string;
  financial_readiness: string;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1.5 text-sm border-b border-gray-100 last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  );
}

export default function ApplicantCard({ applicant }: { applicant: Applicant }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">{applicant.name}</h2>
      <div>
        <Row label="Program" value={applicant.program_name} />
        <Row label="Admission Term" value={applicant.admission_term} />
        <Row label="Nationality" value={applicant.nationality} />
        <Row label="Sponsorship" value={applicant.sponsorship_status} />
        <Row label="Financial Readiness" value={applicant.financial_readiness} />
      </div>
    </div>
  );
}
