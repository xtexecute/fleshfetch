#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float exposure;
    float scan;
    vec2 bodyOrigin;
    vec2 bodySize;
    vec2 bodySquish;
    float bodyAngle;
    float pixelSize;
};
layout(binding = 1) uniform sampler2D silhouette;

float opacityAt(vec2 uv) {
    float inside = step(0.0, min(uv.x, uv.y)) * step(max(uv.x, uv.y), 1.0);
    return texture(silhouette, clamp(uv, 0.0, 1.0)).a * inside;
}

void main() {
    vec2 pixel = floor(qt_TexCoord0 * vec2(92.0, 90.0));
    vec2 center = (pixel + 0.5) / vec2(92.0, 90.0);
    float falloff = dot((center - 0.5) * vec2(0.80, 0.94), (center - 0.5) * vec2(0.80, 0.94));
    float dither = mod(pixel.x + mod(pixel.y, 2.0) * 3.0, 4.0) / 4.0;
    float shade = floor((1.0 - falloff * 1.35) * 18.0 + dither) / 18.0;
    vec3 face = mix(vec3(0.58, 0.64, 0.57), vec3(0.94, 0.93, 0.77), shade);
    float sweep = (1.0 - smoothstep(0.004, 0.095, abs(center.y - scan))) * step(scan, 0.99);
    face = mix(face, vec3(0.96, 0.985, 0.89), min(0.80, exposure * 0.68 + sweep * 0.36));

    // A short, soft contact shadow follows the original sprite's alpha and pose.
    vec2 local = qt_TexCoord0 * vec2(92.0, 90.0) * pixelSize
               - bodyOrigin - bodySize * 0.5 - vec2(1.5, 3.0) * pixelSize;
    float c = cos(bodyAngle), s = sin(bodyAngle);
    vec2 uv = mat2(c, -s, s, c) * local / max(bodySize * bodySquish, vec2(0.01)) + 0.5;
    vec2 blur = vec2(0.015, 0.024);
    float shadow = opacityAt(uv) * 0.40 + 0.15 * (opacityAt(uv + blur)
                 + opacityAt(uv - blur) + opacityAt(uv + vec2(blur.x, -blur.y))
                 + opacityAt(uv + vec2(-blur.x, blur.y)));
    face *= 1.0 - shadow * (0.25 - exposure * 0.08);

    float border = step(min(min(pixel.x, 91.0 - pixel.x), min(pixel.y, 89.0 - pixel.y)), 0.5);
    face = mix(face, vec3(0.67, 0.72, 0.62) + exposure * 0.12, border);
    float ticks = step(mod(pixel.y - 4.0, 8.0), 0.5)
                * max(step(pixel.x, 2.0), step(88.0, pixel.x));
    face = mix(face, vec3(0.45, 0.52, 0.43), ticks * 0.60);
    fragColor = vec4(face, 1.0) * qt_Opacity;
}
