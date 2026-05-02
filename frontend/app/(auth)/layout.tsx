import LanguageToggle from "@/components/LanguageToggle";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#003087] to-[#001a4d] p-4 relative">
      <div className="absolute top-4 right-4 z-10">
        <LanguageToggle variant="light" />
      </div>
      {children}
    </div>
  );
}
