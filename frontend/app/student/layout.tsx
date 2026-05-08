import StudentSidebar from "@/components/layout/StudentSidebar";
import { OnboardingTour } from "@/components/OnboardingTour";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <StudentSidebar />
      <main className="flex-1 bg-gray-50 p-6 overflow-auto">
        {children}
      </main>
      <OnboardingTour />
    </div>
  );
}