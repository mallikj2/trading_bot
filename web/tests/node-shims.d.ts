declare module 'node:test' { export default function test(name: string, fn: () => void): void; }
declare module 'node:assert/strict' { const assert: { equal(a: unknown,b: unknown): void; deepEqual(a: unknown,b: unknown): void; }; export default assert; }
