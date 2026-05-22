'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { registerSchema, type RegisterFormValues } from '@/lib/validations/auth'
import { useAuthStore } from '@/store/authstore'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'

export function RegisterForm() {
  const router = useRouter()
  const registerUser = useAuthStore((s) => s.register)
  const isLoading = useAuthStore((s) => s.isLoading)
  const [rootError, setRootError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterFormValues) => {
    setRootError(null)
    try {
      await registerUser(data.email, data.password)
      router.push('/dashboard')
    } catch (err) {
      setRootError(err instanceof Error ? err.message : 'Registration failed')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="Email"
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register('email')}
      />
      <Input
        label="Password"
        type="password"
        autoComplete="new-password"
        error={errors.password?.message}
        {...register('password')}
      />
      <Input
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        error={errors.confirmPassword?.message}
        {...register('confirmPassword')}
      />
      {rootError && (
        <p className="rounded-lg bg-error/10 px-3 py-2 text-sm text-error" role="alert">
          {rootError}
        </p>
      )}
      <Button type="submit" loading={isLoading} className="w-full">
        Create account
      </Button>
    </form>
  )
}
