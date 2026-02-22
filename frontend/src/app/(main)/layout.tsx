import { AppSidebar } from "@/components/app-sidebar";
import { SidebarProvider } from "@/components/ui/sidebar";

export default function MainLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <SidebarProvider className="h-screen overflow-hidden flex w-full">
            <AppSidebar />
            <main className="flex-1 min-h-0 overflow-hidden w-full">
                {children}
            </main>
        </SidebarProvider>
    );
}
