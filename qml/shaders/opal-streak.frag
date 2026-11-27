#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float fill;
    float phase;
    vec2 viewport;
    vec3 ripple0;
    vec3 ripple1;
    vec3 ripple2;
    vec3 ripple3;
    vec3 ripple4;
    vec3 ripple5;
};

vec2 waveAt(vec3 wave, float x) {
    if (wave.y >= 1.0) return vec2(0.0);
    float distance = abs(x - wave.x * viewport.x);
    float crest = distance - wave.y * viewport.x * 0.82;
    float spread = 6.0 + wave.y * 16.0;
    float fade = pow(1.0 - wave.y, 1.65) * smoothstep(0.0, 0.045, wave.y);
    float envelope = exp(-crest * crest / (spread * spread)) * fade;
    return vec2(sin(crest * 0.19) * envelope * 3.8, envelope);
}

vec3 reflection(float at) {
    float t = fract(at) * 4.0;
    if (t < 1.0) return mix(vec3(0.94, 0.57, 0.74), vec3(0.45, 0.81, 0.87), t);
    if (t < 2.0) return mix(vec3(0.45, 0.81, 0.87), vec3(0.60, 0.82, 0.62), t - 1.0);
    if (t < 3.0) return mix(vec3(0.60, 0.82, 0.62), vec3(0.98, 0.84, 0.51), t - 2.0);
    return mix(vec3(0.98, 0.84, 0.51), vec3(0.94, 0.57, 0.74), t - 3.0);
}

vec3 patchColor(vec3 color, vec2 flow, float seed) {
    float saturation = sin(flow.x * 1.35 + flow.y * 0.73 + phase * 2.0 + seed)
                     * cos(flow.y * 1.16 - phase + seed * 0.63);
    saturation = 0.78 + smoothstep(-0.20, 0.80, saturation) * 1.10;
    float light = dot(color, vec3(0.2126, 0.7152, 0.0722));
    return clamp(mix(vec3(light), color, saturation), 0.0, 1.0);
}

void main() {
    if (fill <= 0.0) {
        fragColor = vec4(0.0);
        return;
    }
    vec2 p = qt_TexCoord0 * viewport;
    float level = clamp(fill / 100.0, 0.0, 1.0);
    float top = viewport.y * (1.0 - level * 0.84);
    vec2 ripple = waveAt(ripple0, p.x) + waveAt(ripple1, p.x)
                + waveAt(ripple2, p.x) + waveAt(ripple3, p.x)
                + waveAt(ripple4, p.x) + waveAt(ripple5, p.x);
    float surface = top + 2.5 * sin(p.x * 0.037 + phase * 4.0)
                  + 1.3 * sin(p.x * 0.071 - phase * 3.0) + clamp(ripple.x, -5.0, 5.0);
    float depth = p.y - surface;
    float alpha = smoothstep(-0.65, 0.65, depth);
    if (alpha == 0.0) {
        fragColor = vec4(0.0);
        return;
    }

    vec2 flow = vec2(p.x, depth) / max(viewport.x, 1.0) * 4.0;
    // Coupled curls carry each color through the pool as its coverage fades.
    for (int i = 0; i < 2; ++i) {
        vec2 curlFlow = vec2(sin(flow.y * 1.7 + phase * 2.0 + float(i)),
                             cos(flow.x * 1.9 - phase + float(i)));
        flow += curlFlow * 0.40;
    }
    float bend = sin(flow.x * 2.2 + flow.y * 1.1 + phase
                     + sin(flow.y * 2.6 - phase) * 0.8);
    float curl = cos(flow.y * 2.7 - flow.x * 1.3 - phase * 2.0
                     + sin(flow.x * 1.8 + phase) * 0.7);
    float pink = smoothstep(0.05, 0.91, sin(bend * 2.0 + flow.y + phase * 2.0))
               * smoothstep(-0.50, 0.75, sin(flow.x * 0.9 + phase * 2.0));
    float cyan = smoothstep(-0.15, 0.90, sin(flow.x * 1.9 + flow.y * 2.2 - phase + bend))
               * smoothstep(-0.55, 0.78, cos(flow.y * 0.9 - phase * 2.0));
    float green = smoothstep(0.08, 0.94, cos(flow.x * 2.1 - flow.y * 2.8 + phase + curl))
                * smoothstep(-0.40, 0.72, sin(flow.x * 0.8 + flow.y + phase));
    float gold = smoothstep(0.18, 0.96, sin(flow.x * 2.5 + curl * 1.7 + phase * 2.0))
               * smoothstep(-0.45, 0.80, cos(flow.x + flow.y * 0.7 - phase * 3.0));
    vec3 milk = vec3(0.69, 0.76, 0.77) + 0.060 * exp(-depth / 95.0);
    vec3 color = mix(milk, patchColor(vec3(0.95, 0.48, 0.73), flow, 0.0), pink * 0.64);
    color = mix(color, patchColor(vec3(0.30, 0.78, 0.90), flow, 1.7), cyan * 0.68);
    color = mix(color, patchColor(vec3(0.47, 0.82, 0.54), flow, 3.4), green * 0.52);
    color = mix(color, patchColor(vec3(0.98, 0.80, 0.38), flow, 5.1), gold * 0.56);

    float reflected = sin(flow.x * 3.2 - flow.y * 1.9 + bend * 1.1 + phase);
    float silver = pow(max(0.0, reflected), 12.0);
    color += vec3(0.10, 0.11, 0.12) * silver;
    float crestLight = exp(-max(depth, 0.0) / 4.5);
    float impactLight = min(1.4, ripple.y) * exp(-max(depth, 0.0) / 12.0);
    vec3 fire = reflection(qt_TexCoord0.x * 0.72 + bend * 0.14 + sin(phase) * 0.12);
    color = mix(color, fire, clamp(crestLight * 0.44 + impactLight * 0.60, 0.0, 0.83));
    float rim = 1.0 - smoothstep(0.35, 1.9, abs(depth));
    color = mix(color, vec3(0.97, 0.985, 0.92), rim * (0.66 + min(0.28, ripple.y * 0.28)));
    color += vec3(0.07, 0.075, 0.055) * impactLight;
    fragColor = vec4(clamp(color, 0.0, 1.0) * alpha, alpha) * qt_Opacity;
}
