

def show():
    return f"""
        <svg width="840" height="260" xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">
            <rect width="840" height="260" rx="14" fill="#ffffff" stroke="#e0e0e0" stroke-width="1.5"/>
        
            <!-- HEADER -->
            <rect x="0" y="0" width="840" height="42" rx="14" fill="#1565c0"/>
            <rect x="0" y="20" width="840" height="22" fill="#1565c0"/>
            <text x="20" y="26" fill="#ffffff" font-size="14" font-weight="bold">VOTRE REPÈRE NUTRITIONNEL : LEMON LIME</text>

            <!-- SEPARATEURS VERTICAUX -->
            <line x1="200" y1="60" x2="200" y2="240" stroke="#eeeeee" stroke-width="2"/>
            <line x1="610" y1="60" x2="610" y2="240" stroke="#eeeeee" stroke-width="2"/>

            <!-- BLOC 1 : Portion & Kcal -->
            <text x="100" y="75" font-size="14" fill="#616161" font-weight="bold" text-anchor="middle">Portion</text>
            <text x="100" y="95" font-size="16" fill="#333" text-anchor="middle">100 g</text>

            <circle cx="100" cy="160" r="46" fill="#e8f5e9" stroke="#43A047" stroke-width="3"/>
            <text x="100" y="160" font-size="26" font-weight="800" fill="#2e7d32" text-anchor="middle">8</text>
            <text x="100" y="182" font-size="14" font-weight="bold" fill="#2e7d32" text-anchor="middle">kcal</text>

            <!-- BLOC 2 : Jauge Macros -->
            <text x="220" y="75" font-size="14" fill="#616161" font-weight="bold">Répartition énergétique</text>

            <!-- ClipPath pour arrondir toute la jauge -->
            <defs>
                <clipPath id="barClip">
                    <rect x="0" y="0" width="380" height="28" rx="6"/>
                </clipPath>
            </defs>

            <g transform="translate(220, 100)" clip-path="url(#barClip)">
                <!-- Fond gris clair si 0 kcal -->
                <rect x="0" y="0" width="380" height="28" fill="#f5f5f5"/>

                <!-- Glucides + Sucres -->
                <rect x="0" y="0" width="380.0" height="28" fill="#42a5f5"/>
                <rect x="0.0" y="0" width="380.0" height="28" fill="#1565c0"/>

                <!-- Protéines -->
                <rect x="380.0" y="0" width="0.0" height="28" fill="#66bb6a"/>

                <!-- Lipides + Saturés (Hachure simulée par couleur sombre alignée à droite de sa section) -->
                <rect x="380.0" y="0" width="0.0" height="28" fill="#ffa726"/>
                <rect x="380.0" y="0" width="0.0" height="28" fill="#e65100"/>
            </g>

            <!-- Textes sous jauge -->
            <text x="220" y="155" font-size="13" font-weight="bold" fill="#1565c0">■ Glucides</text>
            <text x="220" y="172" font-size="13" fill="#333">1.9 g</text>
            <text x="220" y="190" font-size="11" fill="#757575">dont sucres : 1.9 g</text>

            <text x="330" y="155" font-size="13" font-weight="bold" fill="#2e7d32">■ Protéines</text>
            <text x="330" y="172" font-size="13" fill="#333">0.0 g</text>

            <text x="440" y="155" font-size="13" font-weight="bold" fill="#e65100">■ Lipides</text>
            <text x="440" y="172" font-size="13" fill="#333">0.0 g</text>
            <text x="440" y="190" font-size="11" fill="#757575">dont saturés : 0.0 g</text>

            <!-- BLOC 3 : Badges -->
            <text x="630" y="75" font-size="14" fill="#616161" font-weight="bold">Indicateurs</text>

            <rect x="630" y="95" width="180" height="28" rx="6" fill="#c62828" stroke="none" stroke-width="1"/>
            <text x="720" y="114" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="middle">🏭 ULTRA-TRANSFORMÉ</text>

        </svg></div>
        """

print(show())