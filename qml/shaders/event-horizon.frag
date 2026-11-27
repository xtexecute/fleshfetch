#version 440
// Curved-path lookup rendering follows Bruneton, arXiv:2010.08735.
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 viewport;
    float time;
    float energy;
    float lensScale;
    float fill;
    vec2 fleshCenter;
    vec3 impulse0;
    vec3 impulse1;
    vec3 impulse2;
    vec3 impulse3;
};
layout(binding = 1) uniform sampler2D flesh;
layout(binding = 2) uniform sampler2D rays;
layout(binding = 3) uniform sampler2D bodyRays;
layout(binding = 4) uniform sampler2D disc0;
layout(binding = 5) uniform sampler2D disc1;
layout(binding = 6) uniform sampler2D sky;
layout(binding = 7) uniform sampler2D glow;
layout(binding = 8) uniform sampler2D turbulence;

const float pi = 3.14159265359;
const float extent = 10.0;
const float radialMax = 14.14213562373;
const float cameraHeight = 0.27;
const float cameraZ = 0.962860321;
const float shadowRadius = 2.603435;

float decode16(vec2 bytes) {
    return dot(bytes, vec2(65280.0, 255.0)) / 65535.0;
}

float disturbance(vec3 impulse, float r, float angle) {
    if (impulse.y >= 1.0) return 0.0;
    float phase = angle - impulse.x - time * 1.4;
    float angular = pow(max(0.0, 0.5 + 0.5 * cos(phase)), 12.0);
    float crest = r - (8.2 - impulse.y * 4.8);
    return exp(-crest * crest / 0.70) * angular * pow(1.0 - impulse.y, 0.7);
}

vec4 diskColor(vec3 encoded) {
    float r = encoded.r * 8.8;
    if (r < 3.02 || r > 8.80) return vec4(0);
    vec2 axis = normalize(encoded.gb * 2.0 - 1.0);
    float angle = atan(axis.y, axis.x);
    float omega = inversesqrt(2.0 * r * r * r);
    float phase = angle - time * omega * 11.0;
    vec2 uv = vec2(phase / (2.0 * pi) + r * 0.13, r * 0.29);
    vec3 grain = texture(turbulence, fract(uv)).rgb;
    float threads = 0.5 + 0.5 * sin(r * 66.0 + grain.g * 7.0 + sin(phase * 7.0) * 1.8);
    threads *= 1.0 - smoothstep(0.02, 0.10, fwidth(r));
    float density = 0.18 + grain.r * 0.95 + threads * 0.12;
    float beta = sqrt(0.5 / (r - 1.0));
    float doppler = sqrt(1.0 - 1.0 / r) * sqrt(1.0 - beta * beta)
                  / (1.0 - beta * cameraZ * axis.x);
    float heat = pow(max(0.0, (1.0 - sqrt(3.0 / r)) / (r * r * r)) / 0.002056, 0.25);
    float temperature = clamp((heat * doppler - 0.20) / 0.75, 0.0, 1.0);
    vec3 hot = mix(vec3(1.00, 0.22, 0.055), vec3(1.00, 0.72, 0.34), smoothstep(0.0, 0.55, temperature));
    hot = mix(hot, vec3(1.00, 0.97, 0.80), smoothstep(0.48, 0.96, temperature));
    float flare = disturbance(impulse0, r, angle) + disturbance(impulse1, r, angle)
                + disturbance(impulse2, r, angle) + disturbance(impulse3, r, angle);
    float intensity = density * heat * pow(doppler, 2.8) * (1.48 + energy * 0.38 + flare * 2.1);
    vec3 light = hot * intensity * 1.65;
    light = light / (light + 0.40);
    float alpha = smoothstep(3.02, 3.33, r) * (1.0 - smoothstep(7.6, 8.80, r));
    return vec4(light * alpha, alpha);
}

float hash(vec2 cell) {
    return fract(sin(dot(cell, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
    vec2 pixel = qt_TexCoord0 * viewport;
    float halfSize = max(1.0, min(viewport.x, viewport.y) * 0.5);
    vec2 q = (pixel - viewport * 0.5) * vec2(1.0, -1.0) / halfSize * extent / lensScale;
    float radius = max(0.00001, length(q));
    vec2 rayAxis = q / radius;
    vec3 trace = texture(rays, vec2(clamp(radius / radialMax, 0.0, 1.0), 0.5)).rgb;
    float phi = decode16(trace.rg) * (3.0 * pi);
    vec3 radial = vec3(0.0, cameraHeight, cameraZ);
    vec3 tangent = vec3(rayAxis.x, rayAxis.y * cameraZ, -rayAxis.y * cameraHeight);
    vec3 direction = radial * cos(phi) + tangent * sin(phi);
    vec3 color = vec3(0.012, 0.014, 0.019);
    if (trace.b > 0.5) {
        vec2 skyUv = vec2(atan(direction.x, direction.z) / (2.0 * pi) + 0.5,
                         asin(clamp(direction.y, -1.0, 1.0)) / pi + 0.5);
        color += texture(sky, skyUv).rgb * 0.75;
        vec3 bodyTrace = texture(bodyRays, vec2(clamp(radius / radialMax, 0.0, 1.0), 0.5)).rgb;
        if (bodyTrace.b > 0.5 && radius < radialMax) {
            float distance = tan((decode16(bodyTrace.rg) - 0.5) * pi) * 24.0;
            vec2 bodyUv = (rayAxis * distance - fleshCenter) / 9.2 * vec2(1.0, -1.0) + 0.5;
            if (min(bodyUv.x, bodyUv.y) >= 0.0 && max(bodyUv.x, bodyUv.y) <= 1.0) {
                vec4 image = texture(flesh, bodyUv);
                color = color * (1.0 - image.a) + image.rgb * vec3(0.94, 0.90, 0.88);
            }
        }
    } else {
        color = vec3(0.0008, 0.0010, 0.0015);
    }

    float streak = clamp(fill / 100.0, 0.0, 1.0);
    if (streak > 0.0) {
        float top = viewport.y * (1.0 - streak * 0.32);
        vec2 dustCell = floor((pixel + vec2(time * 2.0, -time * 1.6)) / 2.0);
        float speck = smoothstep(0.955, 0.995, hash(dustCell));
        float bed = smoothstep(top, top + 22.0, pixel.y) * streak;
        vec3 material = mix(vec3(0.32, 0.38, 0.46), vec3(0.77, 0.42, 0.22), hash(dustCell + 2.0));
        color += material * speck * bed * 0.55;
    }

    vec2 discUv = q / (2.0 * extent) * vec2(1.0, -1.0) + 0.5;
    if (min(discUv.x, discUv.y) >= 0.0 && max(discUv.x, discUv.y) <= 1.0) {
        vec3 bloom = texture(glow, discUv).rgb;
        bloom *= smoothstep(shadowRadius * 0.88, shadowRadius * 1.05, radius);
        color += bloom * (0.34 + energy * 0.12);
        vec4 back = diskColor(texture(disc1, discUv).rgb);
        vec4 front = diskColor(texture(disc0, discUv).rgb);
        color = color * (1.0 - back.a) + back.rgb;
        color = color * (1.0 - front.a) + front.rgb;
    }
    float ring = exp(-pow((radius - shadowRadius) / 0.028, 2.0));
    color += vec3(0.74, 0.56, 0.35) * ring * (0.16 + energy * 0.06);
    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0) * qt_Opacity;
}
