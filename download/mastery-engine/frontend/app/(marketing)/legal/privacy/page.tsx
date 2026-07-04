'use client'
export default function PrivacyPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="prose prose-slate mx-auto max-w-3xl dark:prose-invert">
        <h1>Privacy Policy</h1>
        <p className="text-muted-foreground">Last updated: July 3, 2026</p>
        <p>This Privacy Policy describes how Mastery Engine ("we", "us", or "our") collects, uses, and protects your information when you use MasteryOS (the "Service").</p>
        <h2>Information We Collect</h2>
        <ul>
          <li><strong>Account information:</strong> email, display name, password (hashed with Argon2id)</li>
          <li><strong>Learning data:</strong> study sessions, answers, mastery scores, progress</li>
          <li><strong>Usage data:</strong> pages visited, features used, device type, browser</li>
          <li><strong>Communication:</strong> feedback, support tickets, emails you send us</li>
        </ul>
        <h2>How We Use Your Information</h2>
        <ul>
          <li>To provide and improve the Service</li>
          <li>To personalize your learning experience</li>
          <li>To send service notifications and updates</li>
          <li>To analyze usage patterns and improve our algorithms</li>
          <li>To prevent fraud and abuse</li>
        </ul>
        <h2>Data Security</h2>
        <p>We use industry-standard security measures including Argon2id password hashing, RS256 JWT authentication, TLS 1.2+ encryption, and encrypted backups. All data is encrypted at rest and in transit.</p>
        <h2>Your Rights (GDPR)</h2>
        <ul>
          <li><strong>Access:</strong> Request a copy of your data</li>
          <li><strong>Rectification:</strong> Correct inaccurate data</li>
          <li><strong>Erasure:</strong> Request deletion of your data</li>
          <li><strong>Portability:</strong> Export your data in JSON format</li>
          <li><strong>Objection:</strong> Opt out of certain processing</li>
        </ul>
        <p>To exercise these rights, email privacy@masteryos.com.</p>
        <h2>Data Retention</h2>
        <p>We retain your data for as long as your account is active. Deleted accounts' data is anonymized after 30 days, except for audit logs which are retained for 2 years for security compliance.</p>
        <h2>Contact</h2>
        <p>Questions? Email privacy@masteryos.com.</p>
      </div>
    </div>
  )
}
