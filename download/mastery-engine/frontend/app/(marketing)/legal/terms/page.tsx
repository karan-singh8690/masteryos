'use client'
export default function TermsPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="prose prose-slate mx-auto max-w-3xl dark:prose-invert">
        <h1>Terms of Service</h1>
        <p className="text-muted-foreground">Last updated: July 3, 2026</p>
        <p>By using MasteryOS, you agree to these Terms of Service.</p>
        <h2>1. Acceptance of Terms</h2>
        <p>By creating an account or using the Service, you agree to be bound by these Terms and our Privacy Policy.</p>
        <h2>2. Use of the Service</h2>
        <p>You may use the Service only for lawful purposes. You must not misuse the Service, attempt to bypass security, or use it to violate any law.</p>
        <h2>3. Account Security</h2>
        <p>You are responsible for safeguarding your account credentials. Enable MFA for additional security. Notify us immediately of any unauthorized access.</p>
        <h2>4. Acceptable Use</h2>
        <ul>
          <li>Do not share your account credentials</li>
          <li>Do not attempt to reverse-engineer or scrape the Service</li>
          <li>Do not use the Service to cheat on interviews or exams</li>
          <li>Do not upload offensive or illegal content</li>
        </ul>
        <h2>5. API Usage</h2>
        <p>API access is subject to rate limits. Do not abuse the API or attempt to circumvent rate limits. API keys must be kept confidential.</p>
        <h2>6. Intellectual Property</h2>
        <p>The Service, including its content, software, and trademarks, is owned by Mastery Engine. Your learning data belongs to you.</p>
        <h2>7. Termination</h2>
        <p>You may delete your account at any time. We may suspend or terminate accounts that violate these Terms.</p>
        <h2>8. Disclaimer</h2>
        <p>The Service is provided "as is" without warranties of any kind. We do not guarantee that the Service will be available at all times.</p>
        <h2>9. Limitation of Liability</h2>
        <p>To the maximum extent permitted by law, Mastery Engine shall not be liable for any indirect, incidental, or consequential damages.</p>
        <h2>10. Changes</h2>
        <p>We may update these Terms from time to time. We will notify users of significant changes via email.</p>
        <h2>Contact</h2>
        <p>Questions? Email legal@masteryos.com.</p>
      </div>
    </div>
  )
}
