import Link from 'next/link'
import { Card } from '@/components/ui/Card'
import { RegisterForm } from '@/components/auth/RegisterForm'

export default function RegisterPage() {
  return (
    <Card title="Create account">
      <RegisterForm />
      <p className="mt-4 text-center text-sm text-text-secondary">
        Already have an account?{' '}
        <Link href="/login" className="text-accent hover:underline">
          Sign in
        </Link>
      </p>
    </Card>
  )
}
