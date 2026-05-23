/** @type {import('next').NextConfig} */
const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
const devBackend = "http://127.0.0.1:8000";

const nextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "production" && apiUrl) {
      return [
        {
          source: "/api/:path*",
          destination: `${apiUrl}/api/:path*`,
        },
      ];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${devBackend}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
