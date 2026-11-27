#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 viewport;
    float radius;
    float time;
    float spin;
    float energy;
    float moonAngle;
    float tideAngle;
    float tide;
    float fill;
    vec4 stroke0;
    vec4 stroke1;
    vec4 stroke2;
    vec4 stroke3;
};
layout(binding = 1) uniform sampler2D surface;
layout(binding = 2) uniform sampler2D weather;

const float pi = 3.14159265359;
vec2 globeUV(vec3 n) { return vec2(atan(n.x, n.z) / (2.0 * pi) + 0.5, asin(clamp(n.y, -1.0, 1.0)) / pi + 0.5); }
vec3 turn(vec3 n, float angle) { float c = cos(angle), s = sin(angle); return vec3(c * n.x + s * n.z, n.y, -s * n.x + c * n.z); }
vec3 field(vec2 uv) { return texture(surface, vec2(fract(uv.x), clamp(uv.y, 0.001, 0.999))).rgb; }
vec3 sky(vec2 uv) { return texture(weather, vec2(fract(uv.x), clamp(uv.y, 0.001, 0.999))).rgb; }

float ripple(vec4 stroke, vec3 n) {
    if (stroke.w >= 1.0) return 0.0;
    float distance = acos(clamp(dot(n, stroke.xyz), -1.0, 1.0));
    float d = distance - stroke.w * 3.0;
    return cos(d * 42.0) * exp(-d * d / 0.012) * pow(1.0 - stroke.w, 1.25) * smoothstep(0.0, 0.055, stroke.w);
}

void main() {
    vec2 pixel = floor(qt_TexCoord0 * viewport) + 0.5;
    vec2 center = viewport * 0.5;
    vec2 p = (pixel - center) / radius;
    float c = cos(tideAngle), s = sin(tideAngle);
    vec2 q = vec2(c * p.x + s * p.y, -s * p.x + c * p.y) / vec2(1.0 + tide, 1.0 - tide * 0.5);
    q = vec2(c * q.x - s * q.y, s * q.x + c * q.y);
    float r2 = dot(q, q);
    vec3 light = normalize(vec3(-0.6, -0.45, 0.72));
    vec3 color = vec3(0);
    float alpha = 0.0;

    float poolTop = viewport.y * (1.0 - 0.84 * clamp(fill / 100.0, 0.0, 1.0));
    float depth = pixel.y - poolTop - sin(pixel.x * 0.045 + time) * (1.5 + energy * 1.5)
        - sin(pixel.x * 0.08 - time * 0.7) - sin(moonAngle) * 2.0;
    float pool = smoothstep(-0.5, 0.5, depth) * step(0.001, fill);
    if (pool > 0.0) {
        float wave = pow(0.5 + 0.5 * sin(pixel.x * 0.08 + sin(depth * 0.07 - time) * 1.5 + time), 15.0);
        color = vec3(0.018, 0.075, 0.18) + vec3(0.10, 0.36, 0.46) * wave * 0.17;
        color += vec3(0.23, 0.66, 0.78) * exp(-max(0.0, depth) / 1.4) * (0.48 + energy * 0.4);
        alpha = pool * 0.94;
        color *= alpha;
    }

    vec2 moonAt = vec2(cos(moonAngle) * 1.23, sin(moonAngle) * 0.53);
    vec2 mq = (p - moonAt) / 0.105;
    float moonR2 = dot(mq, mq);
    bool moonInFront = sin(moonAngle) > 0.0;
    vec3 moonColor = vec3(0);
    if (moonR2 <= 1.0) {
        vec3 normal = vec3(mq, sqrt(1.0 - moonR2));
        vec2 uv = globeUV(turn(normal, time * 0.10));
        float rock = sky(uv).g;
        vec2 d = vec2(1.0 / 768.0, 1.0 / 384.0);
        vec2 gradient = vec2(sky(uv + vec2(d.x, 0)).g - sky(uv - vec2(d.x, 0)).g,
                             sky(uv + vec2(0, d.y)).g - sky(uv - vec2(0, d.y)).g);
        normal = normalize(normal + vec3(-gradient * 3.0, 0));
        float lit = max(0.0, dot(normal, light));
        moonColor = mix(vec3(0.25, 0.30, 0.36), vec3(0.83, 0.82, 0.72), rock) * (0.10 + lit * 0.98);
    }
    if (moonR2 <= 1.0 && !moonInFront) { color = moonColor; alpha = 1.0; }

    float atmosphere = exp(-abs(sqrt(r2) - 1.0) * 48.0) * 0.36;
    if (r2 > 1.0 && r2 < 1.24) {
        float lit = 0.35 + 0.65 * max(0.0, dot(normalize(vec3(q, 0.1)), light));
        float a = atmosphere * lit;
        color = vec3(0.18, 0.53, 0.84) * a + color * (1.0 - a);
        alpha = a + alpha * (1.0 - a);
    }
    if (r2 <= 1.0) {
        vec3 normal = vec3(q, sqrt(1.0 - r2));
        vec3 local = turn(normal, spin);
        vec2 uv = globeUV(local);
        vec3 data = field(uv);
        float land = smoothstep(0.35, 0.65, data.r);
        vec2 d = vec2(1.0 / 768.0, 1.0 / 384.0);
        float coast = clamp(field(uv + vec2(d.x * 3.0, 0)).r + field(uv - vec2(d.x * 3.0, 0)).r
            + field(uv + vec2(0, d.y * 3.0)).r + field(uv - vec2(0, d.y * 3.0)).r - data.r * 4.0, 0.0, 1.0);
        float waves = ripple(stroke0, local) + ripple(stroke1, local) + ripple(stroke2, local) + ripple(stroke3, local);
        float seaDetail = 0.5 + 0.5 * sin(local.x * 72.0 + time * 1.4 + sin(local.y * 55.0 - time) * 1.5);
        vec3 sea = mix(vec3(0.018, 0.11, 0.28), vec3(0.025, 0.31, 0.40), coast * 0.65 + seaDetail * 0.12);
        sea += vec3(0.17, 0.76, 0.85) * max(0.0, waves) * 0.48;
        vec3 ground = mix(vec3(0.40, 0.16, 0.13), vec3(0.80, 0.48, 0.29), data.g * 0.6 + data.b * 0.4);
        ground = mix(vec3(0.77, 0.62, 0.39), ground, smoothstep(0.13, 0.36, data.g));
        float facing = dot(normal, light);
        vec3 base = mix(sea, ground, land);
        vec2 gradient = vec2(field(uv + vec2(d.x, 0)).g - field(uv - vec2(d.x, 0)).g,
                             field(uv + vec2(0, d.y)).g - field(uv - vec2(0, d.y)).g);
        vec3 terrainNormal = normalize(normal + turn(vec3(-gradient * 2.0, 0), -spin) * land);
        float diffuse = max(0.0, dot(terrainNormal, light));
        color = base * (0.075 + diffuse * 1.05);
        float reflection = pow(max(0.0, dot(normal, normalize(light + vec3(0, 0, 1)))), 65.0);
        color += vec3(0.94, 0.87, 0.70) * reflection * (1.0 - land) * (0.55 + seaDetail * 0.20);
        color += vec3(1.0, 0.69, 0.30) * sky(uv).b * (1.0 - smoothstep(-0.12, 0.15, facing)) * land * 1.4;
        vec2 cloudUv = globeUV(turn(normal, spin + time * 0.018 + 0.08));
        float cloud = smoothstep(0.1, 0.8, sky(cloudUv).r);
        float shadow = sky(cloudUv + vec2(-0.008, -0.006)).r * 0.18;
        color *= 1.0 - shadow;
        vec3 cloudColor = mix(vec3(0.055, 0.10, 0.18), vec3(0.86, 0.93, 0.92), smoothstep(-0.1, 0.75, facing));
        color = mix(color, cloudColor, cloud * 0.60);
        float rim = pow(1.0 - normal.z, 3.5);
        color += vec3(0.15, 0.48, 0.73) * rim * smoothstep(-0.4, 0.5, facing) * 0.7;
        alpha = 1.0;
    }
    if (moonR2 <= 1.0 && moonInFront) { color = moonColor; alpha = 1.0; }
    fragColor = vec4(clamp(color, 0.0, 1.0), alpha) * qt_Opacity;
}
