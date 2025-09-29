'use client';

import { useRouter, usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Lock, Unlock, House } from "lucide-react";

export default function NavButton() {
    const router = useRouter();
    const pathname = usePathname();

    return (
        <div className="flex justify-center gap-4 mt-8">
            <Button
                onClick={() => router.push('/')}
                disabled={pathname === '/'}
                size="lg"
                className={`px-6 py-2 ${
                    pathname === '/encrypt'
                        ? 'bg-slate-700 text-white font-medium disabled:bg-slate-400 disabled:cursor-not-allowed'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
                variant={pathname === '/encrypt' ? 'default' : 'outline'}
            >
                <House className="w-4 h-4 mr-2" />
                Home
            </Button>
            <Button
                onClick={() => router.push('/encrypt')}
                disabled={pathname === '/encrypt'}
                size="lg"
                className={`px-6 py-2 ${
                    pathname === '/encrypt'
                        ? 'bg-slate-700 text-white font-medium disabled:bg-slate-400 disabled:cursor-not-allowed'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
                variant={pathname === '/encrypt' ? 'default' : 'outline'}
            >
                <Lock className="w-4 h-4 mr-2" />
                Encrypt
            </Button>
            <Button
                onClick={() => router.push('/decrypt')}
                disabled={pathname === '/decrypt'}
                size="lg"
                className={`px-6 py-2 ${
                    pathname === '/decrypt'
                        ? 'bg-slate-700 text-white font-medium disabled:bg-slate-400 disabled:cursor-not-allowed'
                        : 'border-slate-300 text-slate-700 hover:bg-slate-50'
                }`}
                variant={pathname === '/decrypt' ? 'default' : 'outline'}
            >
                <Unlock className="w-4 h-4 mr-2" />
                Decrypt
            </Button>
        </div>
    );
}