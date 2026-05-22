import Link from 'next/link'
import { Card } from '@/components/ui/Card'
import { LoginForm } from '@/components/auth/LoginForm'

export default function LoginPage() {
  return (
    <Card title="Sign in">
      <LoginForm />
      <p className="mt-4 text-center text-sm text-text-secondary">
        No account?{' '}
        <Link href="/register" className="text-accent hover:underline">
          Register
        </Link>
      </p>
    </Card>
  )
}
