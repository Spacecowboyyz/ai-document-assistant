import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const protectedRoutes = ['/dashboard', '/chat']
const publicRoutes = ['/login', '/register']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const refreshToken = request.cookies.get('refresh_token')?.value

  const isProtected = protectedRoutes.some(route =>
    pathname.startsWith(route)
  )
  const isPublic = publicRoutes.some(route =>
    pathname.startsWith(route)
  )

  if (isProtected && !refreshToken) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (isPublic && refreshToken) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}