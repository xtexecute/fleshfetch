vec3 auroraColor(float height, float fold) {
    vec3 low = mix(vec3(0.12, 0.94, 0.69), vec3(0.21, 0.79, 1.0), fold);
    vec3 high = mix(vec3(0.08, 0.22, 0.64), vec3(0.37, 0.28, 0.76), fold * 0.38);
    return mix(low, high, smoothstep(0.08, 0.95, height));
}

float auroraWave(vec3 stroke, vec2 p) {
    if (stroke.z >= 1.0) return 0.0;
    float d = distance(p, stroke.xy) - stroke.z * 1.2;
    return exp(-d * d / 0.003) * (1.0 - stroke.z) * smoothstep(0.0, 0.06, stroke.z);
}

vec4 auroraCurtain(vec2 p, float time, float flow, float energy, float front,
                   vec3 stroke0, vec3 stroke1, vec3 stroke2, vec3 stroke3) {
    vec3 color = vec3(0);
    float alpha = 0.0;
    for (int i = 0; i < 2; ++i) {
        if (front > 0.5 && i == 1) break;
        float band = float(i);
        float x = p.x + band * 0.035;
        float phase = flow * 0.42 + band * 2.6;
        float fold = sin(x * 10.0 + phase) * 0.5 + 0.5;
        float base = front > 0.5
            ? 0.19 + x * 0.22 + 0.065 * sin(x * 7.0 - phase) + band * 0.085
            : -0.075 - 0.11 * cos(x * 5.0 + phase) + 0.037 * sin(x * 15.0 - phase) + band * 0.055;
        float crest = 0.78 + 0.17 * sin(x * 17.0 - flow * 0.5) + 0.05 * sin(x * 39.0 + flow);
        float tall = (front > 0.5 ? 0.10 + 0.05 * fold : 0.39 + 0.10 * fold) * crest;
        float h = (base - p.y) / tall;
        float ends = 1.0 - smoothstep(0.38, 0.57, abs(x));
        float curtain = smoothstep(-0.03, 0.07, h) * (1.0 - smoothstep(0.25, 1.0, h));
        float bentX = x + 0.032 * h * h * sin(x * 16.0 + h * 2.0 - phase);
        float filaments = pow(0.5 + 0.5 * sin(bentX * 250.0 + 6.0 * sin(bentX * 12.0 + phase) - flow * 2.4), 3.0);
        filaments *= 0.6 + 0.4 * sin(bentX * 81.0 - time * 0.7 + h * 2.0);
        float core = exp(-pow((p.y - base) / (0.007 + fold * 0.008), 2.0));
        float bloom = exp(-pow((p.y - base) / 0.044, 2.0));
        float wave = min(1.4, auroraWave(stroke0, vec2(p.x, base)) + auroraWave(stroke1, vec2(p.x, base))
            + auroraWave(stroke2, vec2(p.x, base)) + auroraWave(stroke3, vec2(p.x, base)));
        float light = (curtain * (0.23 + filaments * 0.53) + core * 0.42 + bloom * 0.08)
            * ends * (0.68 + energy * 0.85 + wave * 1.8) * (front > 0.5 ? 0.55 : 1.0);
        vec3 tint = auroraColor(clamp(h, 0.0, 1.0), fold);
        tint = mix(tint, vec3(0.66, 1.0, 0.94), core * (0.25 + wave * 0.30));
        color += tint * light;
        alpha += light;
    }
    alpha = min(alpha, 0.84);
    return vec4(min(color, vec3(alpha)), alpha);
}
