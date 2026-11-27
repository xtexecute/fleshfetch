#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 view;
    float angle;
    vec3 stroke0;
    vec3 stroke1;
    vec3 stroke2;
    vec3 stroke3;
};
layout(binding = 1) uniform sampler2D source;
layout(binding = 2) uniform sampler2D normals;
layout(binding = 3) uniform sampler2D fire;

vec3 spectral(float t) {
    t = fract(t) * 6.0;
    if (t < 1.0) return mix(vec3(0.15, 0.72, 0.67), vec3(0.20, 0.48, 0.87), t);
    if (t < 2.0) return mix(vec3(0.20, 0.48, 0.87), vec3(0.59, 0.36, 0.76), t - 1.0);
    if (t < 3.0) return mix(vec3(0.59, 0.36, 0.76), vec3(0.93, 0.28, 0.45), t - 2.0);
    if (t < 4.0) return mix(vec3(0.93, 0.28, 0.45), vec3(0.98, 0.60, 0.20), t - 3.0);
    if (t < 5.0) return mix(vec3(0.98, 0.60, 0.20), vec3(0.54, 0.81, 0.26), t - 4.0);
    return mix(vec3(0.54, 0.81, 0.26), vec3(0.15, 0.72, 0.67), t - 5.0);
}

float flare(vec3 stroke, vec2 uv) {
    if (stroke.z >= 1.0) return 0.0;
    float d = distance(uv, stroke.xy) - stroke.z * 0.84;
    return exp(-d * d / 0.012) * (1.0 - stroke.z) * smoothstep(0.0, 0.045, stroke.z);
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec4 body = texture(source, uv);
    if (body.a < 0.001) {
        fragColor = vec4(0);
        return;
    }
    vec3 n = normalize(texture(normals, uv).rgb * 2.0 - 1.0);
    vec3 flake = texture(fire, uv).rgb;
    float c = cos(angle), s = sin(angle);
    n.xy = mat2(c, s, -s, c) * n.xy;
    vec3 camera = normalize(vec3(view * 0.50, 1.0));
    float travel = min(1.4, flare(stroke0, uv) + flare(stroke1, uv) + flare(stroke2, uv) + flare(stroke3, uv));
    float alignment = dot(n.xy, vec2(-1.1, 0.85)) + dot(view, vec2(cos(flake.r * 6.283), sin(flake.r * 6.283))) * 2.2;
    float diffraction = pow(max(0.0, 0.5 + 0.5 * cos(flake.r * 6.283 + alignment * 3.8)),
                            max(2.6, 8.0 - travel * 4.6));
    float fireStrength = flake.g * diffraction * (2.10 + travel * 0.36);
    vec3 tint = spectral(flake.b + alignment * 0.085 + travel * 0.055);
    vec3 milk = body.rgb / body.a;
    vec3 color = mix(milk, tint * (0.63 + milk * 0.42) + vec3(0.065), min(0.84, fireStrength));
    vec3 halfKey = normalize(normalize(vec3(-0.46, 0.65, 0.65)) + camera);
    vec3 halfStrip = normalize(normalize(vec3(0.70, 0.35, 0.64)) + camera);
    float key = pow(max(0.0, dot(n, halfKey)), 32.0);
    float strip = pow(max(0.0, dot(n, halfStrip)), 85.0);
    color += vec3(0.98, 0.98, 0.94) * (key * 0.18 + strip * 0.21);
    vec2 d = vec2(0.004);
    float edge = 1.0 - min(min(texture(source, uv + vec2(d.x, 0)).a, texture(source, uv - vec2(d.x, 0)).a),
                          min(texture(source, uv + vec2(0, d.y)).a, texture(source, uv - vec2(0, d.y)).a));
    color = mix(color, vec3(0.91, 0.95, 0.91), edge * 0.25);
    fragColor = vec4(clamp(color, 0.0, 1.0) * body.a, body.a) * qt_Opacity;
}
