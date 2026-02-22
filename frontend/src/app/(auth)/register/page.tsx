"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/context/session-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";

export default function RegisterPage() {
    const router = useRouter();
    const { setSessionId, triggerRefresh } = useSession();
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            await api.register(email, username, password);
            // Auto login after register
            const data = await api.login(email, password);
            setSessionId(data.session_id);
            triggerRefresh();
            router.push("/");
        } catch (err: any) {
            setError(err.message || "Failed to register account");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 px-4">
            <div className="w-full max-w-md space-y-8 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 p-8 rounded-xl shadow-sm">
                <div className="text-center">
                    <h2 className="text-3xl font-extrabold text-foreground">Create an account</h2>
                    <p className="mt-2 text-sm text-muted-foreground">Join us to start chatting with your PDFs</p>
                </div>
                <form className="mt-8 space-y-6" onSubmit={handleRegister}>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Username</label>
                            <Input
                                type="text"
                                required
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="johndoe"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Email address</label>
                            <Input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@example.com"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-foreground mb-1">Password</label>
                            <Input
                                type="password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="text-destructive text-sm font-medium text-center bg-destructive/10 p-3 rounded-md border border-destructive/20">
                            {error}
                        </div>
                    )}

                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? "Creating account..." : "Register"}
                    </Button>
                </form>

                <div className="text-center mt-4">
                    <p className="text-sm text-muted-foreground">
                        Already have an account?{" "}
                        <Link href="/login" className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400">
                            Sign in here
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
