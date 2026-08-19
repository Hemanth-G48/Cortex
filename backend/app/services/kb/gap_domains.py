"""Curated target-domain knowledge base for the Gap Analysis engine.

Gap Analysis compares *evidence* (from the user's Second Brain) against a
target knowledge map. This module is that map: a curated, human-authored
``Domain → Skill → Concept`` hierarchy with, per concept:

- ``why`` — why the concept matters for the goal/domain,
- ``prereqs`` — prerequisite concept *names* (any domain) that drive the
  learning-path ordering,
- ``learn`` — ordered study sequence,
- ``practice`` — concrete practice actions,
- ``next`` — recommended follow-on concept,
- ``importance`` — 3 critical / 2 important / 1 nice-to-have,
- ``aliases`` — alternate spellings matched against vault concepts.

This is *reference knowledge about a domain* (like a syllabus), never
user-specific data. The engine (`gap_engine.py`) evaluates the user's actual
evidence against these concepts; nothing here claims the user knows anything.

Everything is keyed by concept **name** so the prerequisite graph spans
domains (e.g. Binary Exploitation prerequisites reference "C programming
fundamentals" and "x86-64 assembly" from other domains).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Concept spec helper
# ---------------------------------------------------------------------------

# name, skill, why, prereqs, learn, practice, next, importance, aliases


def C(
    name: str,
    skill: str,
    why: str,
    prereqs: list[str],
    learn: list[str],
    practice: list[str],
    *,
    next: str | None = None,
    importance: int = 2,
    aliases: tuple[str, ...] = (),
) -> dict:
    """Compact concept spec constructor."""
    return {
        "name": name,
        "skill": skill,
        "why": why,
        "prereqs": prereqs,
        "learn": learn,
        "practice": practice,
        "next": next,
        "importance": importance,
        "aliases": list(aliases),
    }


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

DOMAINS: dict[str, dict] = {}


def _domain(
    name: str,
    keywords: list[str],
    skills: list[str],
    concepts: list[dict],
) -> None:
    DOMAINS[name] = {
        "title": name,
        "keywords": [k.lower() for k in keywords],
        "skills": skills,
        "concepts": concepts,
    }


_domain(
    "Cybersecurity Foundations",
    keywords=["cyber", "security", "ctf", "infosec", "hacking", "pentest"],
    skills=["Linux", "Networking", "Programming", "Tooling"],
    concepts=[
        C(
            "Linux fundamentals",
            "Linux",
            "The working environment for virtually every security task — CTF challenges, labs, and jobs all assume shell fluency.",
            [],
            ["Shell navigation & file permissions", "Processes, users, and package management", "Pipes, redirection, and job control"],
            ["Complete a Linux basics lab (e.g. OverTheWire Bandit 0–10)", "Script a small file-organizing task in the shell"],
            next="Command-line tools", importance=3,
        ),
        C(
            "Networking fundamentals",
            "Networking",
            "Security attacks, forensics, and networking roles all build on how data moves between machines.",
            [],
            ["OSI vs TCP/IP model", "IP addressing, ports, and DNS", "Sockets and the client/server model"],
            ["Trace a request with traceroute / curl -v", "Explain each layer for a webpage load"],
            next="HTTP fundamentals", importance=3,
        ),
        C(
            "HTTP fundamentals",
            "Networking",
            "The backbone protocol for web security: every web attack is a manipulation of an HTTP exchange.",
            ["Networking fundamentals"],
            ["Request/response structure, methods, status codes", "Headers, cookies, and URL anatomy", "Same-origin policy basics"],
            ["Inspect requests in a browser devtools / Burp", "Hand-craft a request with curl and netcat"],
            next="Authentication", importance=3,
        ),
        C(
            "Command-line tools",
            "Tooling",
            "grep, find, curl, netcat and friends are the daily toolkit for recon, exploitation, and forensics.",
            ["Linux fundamentals"],
            ["Text processing (grep/awk/sed)", "Network tools (curl, netcat, nmap basics)", "File inspection (file, strings, hexdump)"],
            ["Use each tool on a sample file/URL", "Automate a recon one-liner"],
            next="Scripting", importance=2,
        ),
        C(
            "Scripting",
            "Tooling",
            "Automating analysis and exploits with Python/Bash turns one-off attacks into repeatable tooling.",
            ["Linux fundamentals", "Programming fundamentals"],
            ["Python basics: strings, files, requests, sockets", "Bash loops and argument parsing", "Error handling and debugging"],
            ["Write a small brute-force/login script", "Parse a packet capture with a script"],
            importance=2,
        ),
        C(
            "C programming fundamentals",
            "Programming",
            "The foundation of binary exploitation — memory corruption is only meaningful if you read C's memory model.",
            [],
            ["Syntax: variables, control flow, functions", "Pointers, arrays, and structs", "The memory model: stack vs heap vs globals"],
            ["Write and debug small C programs", "Explain what each pointer dereference touches in memory"],
            next="Memory layout", importance=3,
        ),
    ],
)

_domain(
    "Web Security",
    keywords=["web security", "web app", "web application", "pentest web", "bug bounty"],
    skills=["Web Fundamentals", "Access Control", "Injection", "Server-Side Attacks", "Client-Side Attacks"],
    concepts=[
        C(
            "Authentication",
            "Web Fundamentals",
            "Identity is the front door of every web app — flawed auth is the most common critical finding.",
            ["HTTP fundamentals"],
            ["Password flows, MFA, and account enumeration", "Session tokens and how they are issued", "Common auth bypass patterns"],
            ["Practice auth bypass labs", "Review a login flow and map failure paths"],
            next="Authorization", importance=3,
        ),
        C(
            "Authorization",
            "Web Fundamentals",
            "Broken access control tops OWASP lists: knowing what a user *may* do is separate from proving who they are.",
            ["Authentication"],
            ["RBAC vs object-level access control", "IDOR and privilege escalation patterns", "Horizontal vs vertical escalation"],
            ["Test object-level access control on a lab", "Enumerate endpoints reachable without auth"],
            next="Authentication bypass", importance=3,
        ),
        C(
            "Session security",
            "Web Fundamentals",
            "Session tokens are the keys — fixation, hijacking, and predictable tokens defeat them.",
            ["Authentication", "HTTP fundamentals"],
            ["Cookie flags (HttpOnly, Secure, SameSite)", "Session fixation and hijacking", "Predictable-token analysis"],
            ["Analyze cookie flags on a test app", "Attempt session fixation in a lab"],
            next="CSRF", importance=2,
        ),
        C(
            "CSRF",
            "Client-Side Attacks",
            "Cross-Site Request Forgery turns the victim's browser into an attacker — a classic client-side flaw.",
            ["HTTP fundamentals", "Session security"],
            ["How CSRF works (state-changing GET/POST)", "Tokens, SameSite, and other defenses", "CSRF against JSON/API endpoints"],
            ["Solve beginner then advanced CSRF labs", "Explain the SameSite mitigation chain"],
            next="XSS", importance=2,
        ),
        C(
            "SSRF",
            "Server-Side Attacks",
            "Server-Side Request Forgery is a top web vulnerability and a bridge to internal networks and cloud metadata.",
            ["HTTP fundamentals", "Networking fundamentals"],
            ["How SSRF works (server making requests)", "Accessing localhost / internal services", "Cloud metadata attacks (169.254.169.254)", "Filter bypass techniques"],
            ["Solve 3 beginner → 2 intermediate SSRF labs", "Try SSRF on a local test service"],
            next="XXE", importance=3,
        ),
        C(
            "Path traversal",
            "Server-Side Attacks",
            "Reading arbitrary files through unsanitized paths is a fast, common win in pentests.",
            ["HTTP fundamentals"],
            ["../ traversal and URL encoding tricks", "Absolute paths and null-byte history", "Defense: canonicalization"],
            ["Solve path traversal labs", "Test a file-download endpoint"],
            next="File upload vulnerabilities", importance=2,
        ),
        C(
            "SQL injection",
            "Injection",
            "SQLi is the classic data-exfiltration vulnerability — it still tops real-world breach chains.",
            ["HTTP fundamentals", "SQL basics"],
            ["Detecting SQLi (error/boolean/time-based)", "UNION-based data extraction", "Blind injection automation and defenses"],
            ["Solve SQLi labs across 3 flavors", "Hand-write a UNION payload"],
            next="Command injection", importance=3,
        ),
        C(
            "XSS",
            "Client-Side Attacks",
            "Cross-site scripting is the most common client-side bug and the seed of session theft and account takeover.",
            ["HTTP fundamentals"],
            ["Reflected, stored, and DOM XSS", "CSP and encoding defenses", "Exploiting XSS to steal tokens"],
            ["Solve XSS labs (all 3 types)", "Craft a cookie-stealing payload"],
            next="CSRF", importance=3,
        ),
        C(
            "XXE",
            "Server-Side Attacks",
            "XML External Entities read files and hit internal endpoints when parsers trust DTDs.",
            ["HTTP fundamentals", "XML parsing"],
            ["How XML entities are expanded", "File read and SSRF via XXE", "Blind XXE (out-of-band)"],
            ["Solve XXE labs (basic → blind)", "Craft an entity that reads /etc/passwd"],
            next="SSRF", importance=2,
        ),
        C(
            "SSTI",
            "Server-Side Attacks",
            "Server-Side Template Injection turns template syntax into RCE — common in custom web apps.",
            ["HTTP fundamentals", "Server-side templating"],
            ["Detecting template engines", "Payloads per engine (Jinja2, Twig, Freemarker)", "Escaping to RCE"],
            ["Solve SSTI labs for 2 engines", "Identify the engine from an error"],
            next="Command injection", importance=2,
        ),
        C(
            "Command injection",
            "Injection",
            "Injecting OS commands through shell-string sinks gives direct server control.",
            ["Linux fundamentals", "HTTP fundamentals"],
            ["Shell metacharacters and blind injection", "Detecting via time/out-of-band", "Defenses: input validation, safe APIs"],
            ["Solve command-injection labs", "Chain a blind injection via sleep"],
            next="File upload vulnerabilities", importance=2,
        ),
        C(
            "File upload vulnerabilities",
            "Server-Side Attacks",
            "Uploads that trust filenames/content lead to webshells and stored XSS.",
            ["HTTP fundamentals"],
            ["Extension/content-type bypasses", "Polyglot files and webshell deployment", "Safe storage and serving"],
            ["Bypass an upload filter in a lab", "Deploy a minimal webshell"],
            next="Insecure deserialization", importance=2,
        ),
        C(
            "Insecure deserialization",
            "Server-Side Attacks",
            "Deserializing untrusted objects can execute code (e.g. Java/Python pickle attacks).",
            ["Object serialization", "Programming fundamentals"],
            ["Serialization formats (JSON/XML/pickle/PHP)", "Gadget chains concept", "Detecting and preventing it"],
            ["Solve a deserialization lab", "Trace a gadget chain in a codebase"],
            importance=2,
        ),
        C(
            "Authentication bypass",
            "Access Control",
            "Beyond basic auth flaws: logic bugs, JWT/SSO misconfiguration, and 2FA bypasses.",
            ["Authentication", "Authorization"],
            ["Logic flaws (order of checks, default roles)", "JWT algorithms and signature confusion", "SSO/OAuth misconfigurations"],
            ["Solve auth-bypass labs", "Fuzz a JWT for algorithm confusion"],
            next="SQL injection", importance=2,
        ),
        C(
            "XML parsing",
            "Web Fundamentals",
            "The prerequisite for XXE: understand DTDs, entities, and why parsers expand them.",
            [],
            ["XML structure and DTDs", "Internal vs external entities", "Parser configurations"],
            ["Write a small XML document with a DTD", "Observe entity expansion in a parser"],
            next="XXE", importance=1,
        ),
        C(
            "Server-side templating",
            "Web Fundamentals",
            "Templating engines (Jinja2, Twig, Freemarker) — SSTI attacks target their syntax.",
            ["Programming fundamentals"],
            ["Common template syntax", "Template evaluation context", "Sandboxing and why it fails"],
            ["Render a template in 2 engines", "Spot user input reaching a template"],
            next="SSTI", importance=1,
        ),
    ],
)

_domain(
    "Binary Exploitation",
    keywords=["binary exploitation", "pwn", "binary exploit", "exploit development", "pwn2own"],
    skills=["Foundations", "Memory Corruption", "Mitigations", "Heap", "Modern Exploitation"],
    concepts=[
        C(
            "Memory layout",
            "Foundations",
            "The process memory map (text/data/heap/stack) is the map for every memory-corruption attack.",
            ["C programming fundamentals"],
            ["Segments: text, data, bss, heap, stack", "Where variables live", "Endianness and word size"],
            ["Print addresses of a program's regions", "Sketch a process's memory map"],
            next="Stack frames", importance=3,
        ),
        C(
            "Stack frames",
            "Foundations",
            "Calling conventions and stack layout explain how overflows overwrite return addresses.",
            ["Memory layout", "x86-64 assembly"],
            ["The call stack and frame layout", "Return addresses and saved registers", "Calling conventions (cdecl, SysV)"],
            ["Disassemble a small function", "Identify the saved return address in GDB"],
            next="Buffer overflow", importance=3,
        ),
        C(
            "Buffer overflow",
            "Memory Corruption",
            "The canonical stack smash: overwrite control flow with attacker data.",
            ["Stack frames", "C programming fundamentals"],
            ["Classic stack buffer overflow", "Overwriting return addresses", "Shellcode placement"],
            ["Exploit a stack overflow in a lab", "Get a shell on a deliberately vulnerable binary"],
            next="ret2libc", importance=3,
        ),
        C(
            "Format string",
            "Memory Corruption",
            "printf with attacker-controlled format strings leaks memory and can write arbitrary values.",
            ["Stack frames"],
            ["%x/%p/%n format specifiers", "Reading the stack", "Arbitrary write with %n"],
            ["Leak the stack with %x", "Overwrite a GOT entry in a lab"],
            next="GOT/PLT", importance=3,
        ),
        C(
            "Heap exploitation",
            "Memory Corruption",
            "Modern exploitation usually targets the heap: tcache, fastbins, and use-after-free.",
            ["Memory layout", "Buffer overflow"],
            ["Heap metadata and bins", "Use-after-free and double-free", "Common techniques (tcache poisoning, house of ...)"],
            ["Solve a heap lab", "Trace a use-after-free to an allocator primitive"],
            importance=3,
        ),
        C(
            "Return-oriented programming (ROP)",
            "Modern Exploitation",
            "ROP defeats NX by chaining existing gadgets — the core modern exploitation skill.",
            ["Buffer overflow", "x86-64 assembly"],
            ["Gadgets and the ROP chain concept", "Finding gadgets (ROPgadget/ropper)", "Building a chain (ret2csu, syscalls)"],
            ["Chain 3 gadgets to call a function", "Build a full ROP chain in a lab"],
            next="ret2libc", importance=3,
        ),
        C(
            "GOT/PLT",
            "Modern Exploitation",
            "The GOT/PLT indirection is the favorite overwrite target for redirecting control flow.",
            ["Memory layout", "ELF/PE format"],
            ["PLT stubs and GOT entries", "Lazy binding", "GOT overwrite strategies"],
            ["Read a binary's GOT with readelf", "Overwrite a GOT entry in a lab"],
            next="RELRO", importance=2,
        ),
        C(
            "ASLR",
            "Modern Exploitation",
            "Address Space Layout Randomization randomizes bases — exploitation must leak or brute-force them.",
            ["Memory layout"],
            ["What ASLR randomizes (stack/heap/libc/PIE)", "Defeating it with leaks", "Partial-overwrite tricks"],
            ["Observe ASLR across runs", "Defeat ASLR with a single leak in a lab"],
            importance=3,
        ),
        C(
            "NX",
            "Modern Exploitation",
            "Non-executable stacks forbid shellcode — forcing ROP instead of direct execution.",
            ["Memory layout"],
            ["What NX (W^X) prevents", "Checking protections (checksec)", "ROP as the NX bypass"],
            ["Verify NX with checksec", "ROP a no-execute binary"],
            next="Return-oriented programming (ROP)", importance=3,
        ),
        C(
            "PIE",
            "Modern Exploitation",
            "Position-Independent Executables randomize the binary's own base, protecting against fixed addresses.",
            ["Memory layout", "ELF/PE format"],
            ["What PIE does and how to detect it", "Leaking binary base", "Impact on ROP planning"],
            ["Check PIE with checksec", "Adapt an exploit to a PIE binary"],
            importance=2,
        ),
        C(
            "RELRO",
            "Modern Exploitation",
            "RELRO hardening protects the GOT — full RELRO forces non-GOT targets (hooks, vtable, heap).",
            ["Memory layout", "GOT/PLT"],
            ["Partial vs full RELRO", "Why full RELRO blocks GOT overwrite", "Alternative targets"],
            ["Compare partial vs full RELRO binaries", "Exploit a full-RELRO target via another primitive"],
            importance=2,
        ),
        C(
            "ret2libc",
            "Modern Exploitation",
            "The classic NX bypass: return into libc functions (system) instead of shellcode.",
            ["Buffer overflow", "GOT/PLT"],
            ["Calling system('/bin/sh') via the stack", "Leaking libc base", "One-gadget basics"],
            ["ret2libc with a leaked libc address", "Solve a ret2libc challenge"],
            next="Return-oriented programming (ROP)", importance=3,
        ),
    ],
)

_domain(
    "Cryptography",
    keywords=["crypto", "cryptography", "cryptanalysis"],
    skills=["Foundations", "Symmetric", "Asymmetric", "Hashing", "Attacks"],
    concepts=[
        C(
            "Classical ciphers",
            "Foundations",
            "Caesar/Vigenère/substitution ciphers teach the vocabulary of cryptanalysis before modern crypto.",
            [],
            ["Caesar and ROT13", "Substitution and Vigenère", "Frequency analysis"],
            ["Break a Vigenère cipher by hand", "Use a solver script on a sample"],
            next="Encoding vs encryption", importance=2,
        ),
        C(
            "Encoding vs encryption",
            "Foundations",
            "CTFs constantly hide data in base64/hex/URL encoding — knowing the difference avoids rabbit holes.",
            ["Classical ciphers"],
            ["base64, hex, binary, URL encoding", "Encoding ≠ encryption (no key)", "Recognizing encodings"],
            ["Decode a multi-layer encoding chain", "Identify encodings from ciphertext patterns"],
            next="XOR", importance=2,
        ),
        C(
            "XOR",
            "Foundations",
            "XOR is crypto's workhorse — single-byte, repeating-key, and crib-dragging attacks recur everywhere.",
            ["Encoding vs encryption"],
            ["XOR basics and properties", "Single-byte XOR brute force", "Repeating-key XOR (Vigenère-style) and crib dragging"],
            ["Break single-byte XOR", "Break repeating-key XOR on a real ciphertext"],
            next="Symmetric cryptography", importance=3,
        ),
        C(
            "Modular arithmetic",
            "Foundations",
            "The algebraic foundation of RSA, Diffie-Hellman, and most public-key math.",
            ["Encoding vs encryption"],
            ["Modular addition/multiplication/powers", "GCD, Euclid, modular inverse", "Fermat's little theorem"],
            ["Compute modular inverses by hand", "Implement a fast modular exponent in a script"],
            next="Number theory", importance=3,
        ),
        C(
            "Number theory",
            "Foundations",
            "Primes, Euler's theorem, and factorization are the backbone of RSA-style problems.",
            ["Modular arithmetic"],
            ["Primes, coprimes, φ(n)", "Euler's theorem", "Factoring and why it's hard"],
            ["Compute φ for sample numbers", "Solve a small RSA-style math problem"],
            next="RSA", importance=2,
        ),
        C(
            "Symmetric cryptography",
            "Foundations",
            "Block ciphers (AES/DES) and modes (ECB/CBC/CTR) — and their classic misuse bugs.",
            ["XOR"],
            ["Block vs stream ciphers", "Modes: ECB/CBC/CTR and their weaknesses", "Key reuse dangers"],
            ["Spot ECB from identical blocks", "Decrypt a CBC bit-flip target"],
            next="AES", importance=2,
        ),
        C(
            "RSA",
            "Asymmetric",
            "The most tested public-key scheme — small exponents, unfactored n, and padding errors drive CTF attacks.",
            ["Modular arithmetic", "Number theory"],
            ["Key generation and math", "RSA weaknesses (small e, small d, shared n)", "PKCS#1 padding oracles"],
            ["Solve small-e / common-modulus challenges", "Implement an attack on a generated weak RSA key"],
            next="Common crypto attacks", importance=3,
        ),
        C(
            "AES",
            "Symmetric",
            "AES itself is strong — the fun is misuse: ECB mode, IV reuse, padding oracles.",
            ["Symmetric cryptography"],
            ["AES internals at a high level", "ECB/CBC/CTR weaknesses with AES", "Padding-oracle attacks"],
            ["Solve an ECB cut-and-paste challenge", "Run a padding-oracle attack in a lab"],
            next="Padding & modes", importance=3,
        ),
        C(
            "Hashing",
            "Hashing",
            "Hash functions, MACs, and their failures (length extension, collisions, unsalted hashes).",
            ["Encoding vs encryption"],
            ["Hash properties and common hashes", "Salt and why it matters", "Hash length-extension attacks"],
            ["Crack weak hashes with a wordlist", "Perform a length-extension attack"],
            next="Weak randomness", importance=3,
        ),
        C(
            "Padding & modes",
            "Symmetric",
            "Block-cipher modes and padding schemes create most AES bugs in practice.",
            ["AES"],
            ["CBC padding and PKCS#7", "ECB/CBC/CTR mode attacks", "IV nonce reuse"],
            ["Bit-flip a CBC ciphertext", "Exploit nonce reuse in CTR"],
            next="Common crypto attacks", importance=2,
        ),
        C(
            "Weak randomness",
            "Hashing",
            "Predictable PRNGs and seeds let attackers forge tokens and recover keys.",
            ["Hashing", "Modular arithmetic"],
            ["How PRNGs work (LCG, mt19937)", "Seed recovery and prediction", "Real-world token prediction cases"],
            ["Predict the next LCG output", "Break a seeded 'random' token in a lab"],
            next="Common crypto attacks", importance=3,
        ),
        C(
            "Common crypto attacks",
            "Attacks",
            "The capstone: composing attacks (padding oracle, length extension, related messages) on real targets.",
            ["RSA", "AES", "Hashing", "Weak randomness"],
            ["Padding-oracle and Bleichenbacher basics", "Hash length extension", "Related-message / Franklin-Reiter attacks"],
            ["Solve a multi-step crypto CTF challenge", "Chain two attacks on one challenge"],
            importance=3,
        ),
    ],
)

_domain(
    "Forensics",
    keywords=["forensic", "forensics", "memory forensics", "incident response"],
    skills=["Foundations", "Memory", "Disk", "Network", "Steganography"],
    concepts=[
        C(
            "File analysis",
            "Foundations",
            "Identifying file types by magic bytes and structure is the first step of every forensic challenge.",
            ["Linux fundamentals"],
            ["file, hexdump, binwalk", "Magic bytes and file signatures", "Archive and image formats"],
            ["Identify mystery files with magic bytes", "Extract hidden archives from a blob"],
            next="Metadata analysis", importance=2,
        ),
        C(
            "Metadata analysis",
            "Foundations",
            "EXIF, strings, and timestamps leak authors, devices, and hidden messages.",
            ["File analysis"],
            ["EXIF and document metadata", "strings and entropy analysis", "Timestamps and artifacts"],
            ["Extract EXIF from an image", "Find a hidden flag with strings"],
            next="Steganography", importance=2,
        ),
        C(
            "Memory forensics",
            "Foundations",
            "RAM captures hold running processes, secrets, and malware — Volatility is the standard toolkit.",
            ["File analysis"],
            ["Memory acquisition formats", "Volatility basics (pslist, filescan, dump)", "Finding injected/malicious artifacts"],
            ["Run a Volatility triage on a sample", "Extract a secret from a memory dump"],
            importance=2,
        ),
        C(
            "Disk forensics",
            "Foundations",
            "Filesystems hide data in slack, deleted files, and hidden partitions — carving recovers it.",
            ["File analysis"],
            ["Partition tables and filesystems", "Deleted file recovery", "Carving with foremost/scalpel"],
            ["Carve deleted files from an image", "Recover a file from unallocated space"],
            importance=2,
        ),
        C(
            "Network forensics",
            "Foundations",
            "Reconstructing attacks from traffic: pcap analysis, exfiltration, and beaconing.",
            ["Networking fundamentals", "PCAP analysis"],
            ["Tracing connections and streams", "Spotting exfiltration and beacons", "Protocols of interest (DNS, HTTP, TLS)"],
            ["Analyze a malicious pcap", "Reconstruct a data exfiltration"],
            importance=2,
        ),
        C(
            "PCAP analysis",
            "Foundations",
            "Wireshark/tcpdump fluency — the entry point for every network forensics question.",
            ["Networking fundamentals"],
            ["Wireshark filters and follow-stream", "DNS/HTTP/TCP analysis", "Exporting objects"],
            ["Follow a TCP stream to find a flag", "Export an embedded object from a pcap"],
            next="Network forensics", importance=2,
        ),
        C(
            "Steganography",
            "Foundations",
            "Hiding data inside images/audio — LSB, palettes, and stego tools recur in CTFs.",
            ["File analysis"],
            ["LSB and common stego tools (zsteg, steghide)", "Image structure (PNG/JPEG) basics", "Multi-stage hiding"],
            ["Extract LSB data from an image", "Solve a stego challenge end-to-end"],
            importance=2,
        ),
        C(
            "Log analysis",
            "Foundations",
            "Reading application and auth logs to reconstruct attacker actions.",
            ["Linux fundamentals", "File analysis"],
            ["Common log formats", "Correlating entries over time", "Spotting brute force / anomalies"],
            ["Trace an attack through a log set", "Extract attacker IPs from auth logs"],
            importance=2,
        ),
    ],
)

_domain(
    "Reverse Engineering",
    keywords=["reverse engineering", "reversing", "malware analysis", "crackme"],
    skills=["Foundations", "Static Analysis", "Dynamic Analysis", "Advanced"],
    concepts=[
        C(
            "x86-64 assembly",
            "Foundations",
            "Reading assembly is the core language of RE — registers, instructions, and calling conventions.",
            ["C programming fundamentals"],
            ["Registers, stack, and common instructions", "Calling conventions (SysV)", "Disassembly basics"],
            ["Read a disassembled function", "Trace a small program in GDB"],
            next="Function identification", importance=3,
        ),
        C(
            "ELF/PE format",
            "Foundations",
            "Executable formats, sections, headers, and imports structure everything RE tools show you.",
            ["Memory layout"],
            ["ELF sections/headers", "PE structure (imports, resources)", "readelf/objdump basics"],
            ["Dump sections with readelf", "Identify imports of a binary"],
            next="Static analysis", importance=2,
        ),
        C(
            "GDB",
            "Dynamic Analysis",
            "The debugger for stepping, breakpoints, and inspecting memory at runtime.",
            ["x86-64 assembly"],
            ["Breakpoints and stepping", "Examining registers/memory", "GDB scripts and pwndbg basics"],
            ["Debug a crackme", "Set a breakpoint and inspect the stack"],
            next="Dynamic analysis", importance=2,
        ),
        C(
            "Static analysis",
            "Static Analysis",
            "Reading code without running it: strings, decompilers (Ghidra), and cross-references.",
            ["ELF/PE format"],
            ["strings and object inspection", "Ghidra decompilation workflow", "Following xrefs to key functions"],
            ["Recover the logic of a crackme statically", "Decompile and patch a binary"],
            importance=2,
        ),
        C(
            "Dynamic analysis",
            "Dynamic Analysis",
            "Observing behavior at runtime: debugging, tracing, and syscall analysis.",
            ["GDB", "x86-64 assembly"],
            ["Run-time tracing (strace/ltrace)", "Behavioral sandboxing", "Combining static + dynamic"],
            ["Trace a binary's syscalls", "Bypass a check dynamically"],
            next="Anti-debugging", importance=2,
        ),
        C(
            "Function identification",
            "Static Analysis",
            "Finding the interesting functions (checks, crypto, flag logic) quickly.",
            ["x86-64 assembly"],
            ["Recognizing function prologues", "Strings → xrefs → logic", "Common compiler idioms"],
            ["Locate the 'check' function in a crackme", "Map a binary's call graph"],
            importance=2,
        ),
        C(
            "Anti-debugging",
            "Advanced",
            "ptrace, timing, and obfuscation countermeasures — and how to defeat them.",
            ["Dynamic analysis"],
            ["ptrace self-attach and timing checks", "Obfuscation and packing basics", "Defeating checks"],
            ["Defeat an anti-debug check", "Unpack a packed binary"],
            importance=2,
        ),
    ],
)

_domain(
    "Computer Networks",
    keywords=["computer networks", "computer communication", "networking", "ccn", "network"],
    skills=["Foundations", "Protocols", "Routing", "Security"],
    concepts=[
        C(
            "TCP/IP model",
            "Foundations",
            "The layered model every network course builds on — and where each protocol lives.",
            ["Networking fundamentals"],
            ["The 4/5-layer model", "Encapsulation", "Where TCP/UDP/IP fit"],
            ["Map a packet through the layers", "Capture and inspect with tcpdump"],
            next="TCP handshake", importance=3,
        ),
        C(
            "IP addressing & subnetting",
            "Foundations",
            "Addresses, masks, and CIDR — the arithmetic of every network.",
            ["Networking fundamentals"],
            ["IPv4/IPv6 addressing", "Subnet masks and CIDR", "Public/private addressing"],
            ["Subnet a /24 by hand", "Compute network/broadcast for 5 addresses"],
            next="Routing fundamentals", importance=3,
        ),
        C(
            "DNS",
            "Protocols",
            "The phonebook of the internet — and a common exfiltration/attacker channel.",
            ["Networking fundamentals"],
            ["DNS hierarchy and record types", "Resolution flow", "DNS security issues"],
            ["Trace a lookup with dig +trace", "Explain a DNS rebinding attack"],
            importance=3,
        ),
        C(
            "TLS",
            "Protocols",
            "Transport security: handshake, certificates, and where HTTPS breaks.",
            ["HTTP fundamentals", "Networking fundamentals"],
            ["TLS handshake basics", "Certificates and trust", "TLS in HTTPS"],
            ["Inspect a handshake in Wireshark", "Explain certificate validation failure"],
            next="Network security", importance=3,
        ),
        C(
            "Routing fundamentals",
            "Foundations",
            "How packets find their way: routing tables, static vs dynamic routing.",
            ["IP addressing & subnetting"],
            ["Routing tables and next hops", "Static vs dynamic routing", "Distance-vector vs link-state"],
            ["Trace a route across the internet", "Build a small routing table by hand"],
            next="BGP", importance=2,
        ),
        C(
            "BGP",
            "Routing",
            "The internet's inter-domain routing protocol — and a source of route-hijack incidents.",
            ["Routing fundamentals"],
            ["Autonomous systems", "BGP path selection basics", "Hijacks and filtering"],
            ["Read a BGP announcement (bgp.he.net)", "Explain a route-hijack case"],
            importance=2,
        ),
        C(
            "Packet analysis",
            "Foundations",
            "Reading traffic byte-by-byte to diagnose issues and spot attacks.",
            ["TCP/IP model"],
            ["Wireshark/tcpdump workflows", "Filtering and reassembly", "Common anomalies"],
            ["Analyze a TCP handshake capture", "Find a port scan in a pcap"],
            importance=2,
        ),
        C(
            "Network security",
            "Security",
            "Firewalls, segmentation, and the attacks (spoofing, MITM, DoS) they mitigate.",
            ["TLS", "Routing fundamentals"],
            ["Firewalls and ACLs", "Segmentation and VLANs", "Spoofing/MITM/DoS basics"],
            ["Design a segmented network", "Spot a spoofing pattern in a capture"],
            importance=2,
        ),
        C(
            "TCP handshake",
            "Foundations",
            "The three-way handshake and TCP state — foundational for both networking and network attacks.",
            ["TCP/IP model"],
            ["SYN/ACK flow and states", "Sequence numbers", "Handshake-based attacks"],
            ["Capture and explain a handshake", "Explain a SYN flood"],
            importance=2,
        ),
    ],
)

_domain(
    "Operating Systems",
    keywords=["operating system", "operating systems", "os concepts"],
    skills=["Processes", "Memory", "Storage", "Concurrency"],
    concepts=[
        C(
            "Processes & threads",
            "Processes",
            "The unit of execution — how programs become schedulable work.",
            ["C programming fundamentals"],
            ["Process vs thread", "Process lifecycle and states", "Context switching basics"],
            ["List processes and map their states", "Write a program that forks and execs"],
            next="Scheduling", importance=3,
        ),
        C(
            "Scheduling",
            "Processes",
            "CPU scheduling policies decide responsiveness and fairness.",
            ["Processes & threads"],
            ["FCFS/SJF/RR/priority", "Scheduling metrics", "MLFQ basics"],
            ["Simulate RR with a fixed quantum", "Compare two algorithms on a workload"],
            importance=2,
        ),
        C(
            "Synchronization",
            "Concurrency",
            "Race conditions, mutexes, and semaphores — the hard core of concurrent programming.",
            ["Processes & threads"],
            ["Critical sections and races", "Mutex/semaphore/monitor", "Deadlock and starvation basics"],
            ["Fix a data race", "Solve the producer-consumer problem"],
            next="Deadlocks", importance=3,
        ),
        C(
            "Deadlocks",
            "Concurrency",
            "Four conditions, detection, and prevention — a classic exam and interview topic.",
            ["Synchronization"],
            ["The 4 deadlock conditions", "Detection and avoidance", "Banker's algorithm basics"],
            ["Identify deadlock in a trace", "Prevent deadlock in a small system"],
            importance=2,
        ),
        C(
            "IPC",
            "Concurrency",
            "How processes exchange data: pipes, messages, shared memory.",
            ["Processes & threads"],
            ["Pipes and signals", "Message queues and shared memory", "Sockets as IPC"],
            ["Pass data between two programs", "Use shared memory in a small program"],
            importance=2,
        ),
        C(
            "Virtual memory",
            "Memory",
            "Paging, addresses, and demand paging — why every process gets its own address space.",
            ["Memory layout", "Processes & threads"],
            ["Paging and page tables", "TLB and page faults", "Demand paging and swapping"],
            ["Explain a page fault walk", "Analyze a memory-hungry program's RSS/VSZ"],
            importance=3,
        ),
        C(
            "File systems",
            "Storage",
            "Inodes, directories, and journaling — how storage is organized and recovered.",
            ["Linux fundamentals"],
            ["Files vs directories vs inodes", "Permissions and links", "Journaling basics"],
            ["Inspect a filesystem with stat/lsblk", "Explain a deleted-file recovery path"],
            importance=2,
        ),
    ],
)

_domain(
    "Programming & Data Structures",
    keywords=["programming", "data structure", "algorithms", "computer science", "coding", "oop", "software"],
    skills=["Foundations", "Data Structures", "Algorithms"],
    concepts=[
        C(
            "Programming fundamentals",
            "Foundations",
            "Variables, control flow, functions, and debugging — the universal base.",
            [],
            ["Types, variables, expressions", "Conditionals and loops", "Functions and debugging"],
            ["Build 3 small programs", "Trace a debugger through a bug"],
            next="Arrays & strings", importance=3,
        ),
        C(
            "Object-oriented programming",
            "Foundations",
            "Classes, inheritance, and polymorphism — the dominant paradigm in real codebases.",
            ["Programming fundamentals"],
            ["Classes and objects", "Inheritance and polymorphism", "Encapsulation and interfaces"],
            ["Model a small domain with classes", "Refactor a function into objects"],
            next="Object serialization", importance=2,
        ),
        C(
            "Object serialization",
            "Foundations",
            "Converting objects to bytes (JSON/XML/pickle/PHP) — and the deserialization danger it creates.",
            ["Object-oriented programming"],
            ["Serialization formats", "Round-tripping objects", "Trust boundaries"],
            ["Serialize/deserialize in 2 formats", "Identify untrusted deserialization in code"],
            next="Insecure deserialization", importance=1,
        ),
        C(
            "Arrays & strings",
            "Data Structures",
            "The most common structures — indexing, bounds, and why C strings are dangerous.",
            ["Programming fundamentals"],
            ["Array indexing and bounds", "Strings and their representations", "Multi-dimensional arrays"],
            ["Implement a dynamic array", "Spot an out-of-bounds access"],
            next="Stacks & queues", importance=2,
        ),
        C(
            "Linked lists",
            "Data Structures",
            "Node-based structures teaching pointers and dynamic memory.",
            ["Programming fundamentals"],
            ["Singly/doubly linked lists", "Insertion and deletion", "Cycle detection"],
            ["Implement a linked list", "Detect a cycle in a list"],
            next="Trees & graphs", importance=2,
        ),
        C(
            "Stacks & queues",
            "Data Structures",
            "LIFO/FIFO structures powering call stacks, buffers, and BFS.",
            ["Arrays & strings"],
            ["Stack and queue operations", "Implementations", "Classic uses (undo, BFS)"],
            ["Implement both in code", "Use a stack for expression evaluation"],
            importance=2,
        ),
        C(
            "Trees & graphs",
            "Data Structures",
            "Hierarchical and networked data — traversal and search underpin most algorithms.",
            ["Linked lists"],
            ["Binary trees and BSTs", "Tree traversals", "Graph representations and BFS/DFS"],
            ["Implement a BST", "Run BFS/DFS on a small graph"],
            importance=2,
        ),
        C(
            "Hash tables",
            "Data Structures",
            "O(1) lookup via hashing — the workhorse of modern programming.",
            ["Arrays & strings"],
            ["Hash functions and collisions", "Chaining vs open addressing", "Load factor and resizing"],
            ["Implement a hash map", "Measure collision impact"],
            importance=2,
        ),
        C(
            "Recursion",
            "Algorithms",
            "Functions calling themselves — the basis of divide-and-conquer and tree algorithms.",
            ["Programming fundamentals"],
            ["Recursive structure and base cases", "Recursion vs iteration", "Common recursive patterns"],
            ["Solve 3 problems recursively", "Convert recursion to a loop"],
            next="Sorting & searching", importance=2,
        ),
        C(
            "Sorting & searching",
            "Algorithms",
            "The canonical algorithms: merge/quick sort, binary search, and their complexity.",
            ["Arrays & strings", "Recursion"],
            ["Comparison sorts", "Binary search", "Complexity intuition"],
            ["Implement merge sort", "Binary-search a sorted array"],
            next="Complexity analysis", importance=2,
        ),
        C(
            "Complexity analysis",
            "Algorithms",
            "Big-O reasoning — the language of 'will this scale?' in interviews and design.",
            ["Sorting & searching"],
            ["Big-O/Ω/Θ notation", "Common growth classes", "Analyzing loops and recursion"],
            ["Classify 10 algorithms by complexity", "Analyze a nested-loop function"],
            importance=2,
        ),
    ],
)

_domain(
    "Databases",
    keywords=["database", "databases", "sql", "dbms", "relational"],
    skills=["Foundations", "Design", "Internals"],
    concepts=[
        C(
            "SQL basics",
            "Foundations",
            "CRUD, joins, and queries — and the injection surface they create when built from strings.",
            ["Programming fundamentals"],
            ["SELECT/INSERT/UPDATE/DELETE", "Joins and aggregations", "Subqueries"],
            ["Write queries against a sample schema", "Join 3 tables for a report"],
            next="Normalization", importance=3,
        ),
        C(
            "Normalization",
            "Design",
            "Schema design that removes redundancy and anomalies — 1NF through 3NF.",
            ["SQL basics"],
            ["Functional dependencies", "1NF/2NF/3NF", "Keys and indexes"],
            ["Normalize a messy schema to 3NF", "Identify anomalies in a table"],
            importance=2,
        ),
        C(
            "Transactions",
            "Foundations",
            "ACID properties, isolation levels, and why concurrency corrupts data without them.",
            ["SQL basics"],
            ["ACID and transactions", "Isolation levels", "Locks and optimistic concurrency"],
            ["Trace a lost-update scenario", "Design a transaction-safe flow"],
            importance=2,
        ),
        C(
            "Indexing",
            "Internals",
            "How indexes speed queries (and slow writes) — B-trees and query planning basics.",
            ["SQL basics"],
            ["Index structures (B-tree basics)", "Covering and composite indexes", "EXPLAIN plans"],
            ["EXPLAIN a slow query", "Add an index and measure the change"],
            importance=2,
        ),
    ],
)

_domain(
    "Machine Learning & AI",
    keywords=["machine learning", "artificial intelligence", "ai", "ml", "deep learning"],
    skills=["Foundations", "Models"],
    concepts=[
        C(
            "Probability & statistics",
            "Foundations",
            "Distributions, expectation, and inference — the math underneath every model.",
            ["Programming fundamentals"],
            ["Distributions and expectation", "Conditional probability and Bayes", "Sampling and bias"],
            ["Compute probabilities on a small dataset", "Interpret a confusion matrix"],
            next="Linear regression", importance=2,
        ),
        C(
            "Linear regression",
            "Models",
            "The simplest predictive model — and the launchpad for gradient-based learning.",
            ["Probability & statistics"],
            ["The linear model and loss", "Least squares", "Underfitting/overfitting basics"],
            ["Fit a line to data by hand", "Implement least squares in code"],
            next="Gradient descent", importance=2,
        ),
        C(
            "Gradient descent",
            "Models",
            "The optimizer behind most ML — learning rates, convergence, and local minima.",
            ["Linear regression"],
            ["Gradients and the update rule", "Learning rates and convergence", "Stochastic vs batch"],
            ["Implement gradient descent on a toy loss", "Tune the learning rate and observe"],
            next="Neural networks", importance=2,
        ),
        C(
            "Neural networks",
            "Models",
            "Layers, activations, and backpropagation — the modern workhorse.",
            ["Linear regression", "Gradient descent"],
            ["Neurons, layers, activations", "Backpropagation intuition", "Training loops and data splits"],
            ["Train a small network on a toy set", "Diagnose overfitting"],
            importance=2,
        ),
    ],
)


# ---------------------------------------------------------------------------
# Goals (career / aspiration-level targets)
# ---------------------------------------------------------------------------

GOALS: dict[str, dict] = {
    "ctf": {
        "title": "Cybersecurity CTF",
        "description": "Become strong at capture-the-flag competitions across web, pwn, crypto, forensics, and reversing.",
        "domains": [
            "Cybersecurity Foundations",
            "Web Security",
            "Binary Exploitation",
            "Cryptography",
            "Forensics",
            "Reverse Engineering",
        ],
    },
    "cybersecurity": {
        "title": "Cybersecurity / Pentesting Career",
        "description": "Build the foundations for penetration testing, security engineering, or bug bounty work.",
        "domains": [
            "Cybersecurity Foundations",
            "Web Security",
            "Computer Networks",
            "Cryptography",
            "Binary Exploitation",
            "Forensics",
            "Reverse Engineering",
        ],
    },
    "software-engineering": {
        "title": "Software Engineering",
        "description": "Strengthen programming, data structures, databases, and systems foundations for placements and interviews.",
        "domains": [
            "Programming & Data Structures",
            "Databases",
            "Operating Systems",
            "Computer Networks",
        ],
    },
    "ai-ml": {
        "title": "AI & Machine Learning",
        "description": "Build the math and model fundamentals for ML/DS roles and coursework.",
        "domains": [
            "Programming & Data Structures",
            "Machine Learning & AI",
            "Databases",
        ],
    },
    "networking": {
        "title": "Networking Specialist",
        "description": "Master protocols, routing, and network security for network engineering roles.",
        "domains": [
            "Computer Networks",
            "Cybersecurity Foundations",
            "Programming & Data Structures",
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def all_concepts() -> list[dict]:
    """Every concept spec across all domains (deduped by name)."""
    out: dict[str, dict] = {}
    for domain in DOMAINS.values():
        for spec in domain["concepts"]:
            out.setdefault(spec["name"], spec)
    return list(out.values())


def concepts_by_name() -> dict[str, dict]:
    return {c["name"]: c for c in all_concepts()}


def concepts_for_goal(goal_key: str) -> list[dict]:
    """Concepts for a goal's domains, deduped by name, domain-tagged."""
    goal = GOALS.get(goal_key)
    if not goal:
        return []
    seen: dict[str, dict] = {}
    for domain_name in goal["domains"]:
        domain = DOMAINS.get(domain_name)
        if not domain:
            continue
        for spec in domain["concepts"]:
            entry = dict(spec)
            entry["domain"] = domain_name
            seen.setdefault(entry["name"], entry)
    return list(seen.values())


def domain_for_course(title: str) -> str | None:
    """Best domain match for a course title (keyword substring match)."""
    t = (title or "").strip().lower()
    if not t:
        return None
    best: tuple[int, str] | None = None
    for name, domain in DOMAINS.items():
        for kw in domain["keywords"]:
            if kw in t:
                score = len(kw)
                if best is None or score > best[0]:
                    best = (score, name)
    return best[1] if best else None


def goals_payload() -> list[dict]:
    """Goal list for the UI (goal → domains)."""
    return [
        {
            "key": key,
            "title": goal["title"],
            "description": goal["description"],
            "domains": goal["domains"],
        }
        for key, goal in GOALS.items()
    ]
