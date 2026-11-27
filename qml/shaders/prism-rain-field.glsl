vec3 prismColor(int band) {
    if (band == 0) return vec3(0.98, 0.31, 0.40);
    if (band == 1) return vec3(1.00, 0.56, 0.25);
    if (band == 2) return vec3(1.00, 0.83, 0.38);
    if (band == 3) return vec3(0.40, 0.89, 0.63);
    if (band == 4) return vec3(0.28, 0.80, 0.93);
    if (band == 5) return vec3(0.41, 0.55, 1.00);
    return vec3(0.74, 0.42, 0.94);
}

vec4 prismSpectrum(vec2 at, vec2 emitter, float extent, float energy, float sweep) {
    vec2 p = (at - emitter) / extent;
    if (p.y < 0.0 || p.y > 1.3) return vec4(0.0);
    float flare = pow(max(0.0, 1.0 - abs(p.y - (sweep * 1.3)) / 0.19), 2.0) * energy;
    float fade = smoothstep(0.0, 0.065, p.y) * (1.0 - smoothstep(0.72, 1.3, p.y));
    float width = 0.0025 + p.y * (0.009 + energy * 0.010);
    vec3 color = vec3(0);
    float alpha = 0.0;
    for (int i = 0; i < 7; ++i) {
        float slope = -0.48 + float(i) * 0.15;
        float distance = abs(p.x - p.y * slope);
        float core = 1.0 - smoothstep(width * 0.65, width + 0.003, distance);
        float glow = 1.0 - smoothstep(width, width + 0.021, distance);
        float strength = (core + glow * 0.16) * (0.065 + energy * 0.43 + flare * 0.45) * fade;
        color += prismColor(i) * strength;
        alpha += strength;
    }
    return vec4(min(color, vec3(0.86)), min(alpha, 0.86));
}
