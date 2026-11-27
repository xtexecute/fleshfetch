#version 440
#extension GL_GOOGLE_include_directive : enable
#include "sundial-light.glsl"

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float sunAngle;
    float bodyAngle;
    vec2 bodySquish;
    vec2 bodySize;
    float pixelGrid;
};
layout(binding = 1) uniform sampler2D silhouette;

const vec2 dialCenter = vec2(0.50, 0.685);
const vec2 dialAxes = vec2(0.449, 0.249);
const vec2 arcCenter = vec2(0.50, 0.353);
const vec2 arcAxes = vec2(0.385, 0.246);
const float tau = 6.2831853;

float disc(float d, float radius) {
    return step(d, radius);
}

vec4 over(vec4 bottom, vec3 color, float alpha) {
    return vec4(color * alpha, alpha) + bottom * (1.0 - alpha);
}

float grain(vec2 p) {
    vec2 cell = floor(p);
    return fract(52.9829189 * fract(dot(cell, vec2(0.06711056, 0.00583715))));
}

float tone(float value, float levels) {
    return floor(clamp(value, 0.0, 1.0) * levels + 0.5) / levels;
}

float alphaAt(vec2 uv) {
    return texture(silhouette, clamp(uv, 0.0, 1.0)).a
         * step(0.0, min(uv.x, uv.y)) * step(max(uv.x, uv.y), 1.0);
}

float castShadow(vec2 p, float side, float elevation) {
    // Project the moving sprite onto the flattened dial plane.
    float low = 1.0 - max(elevation, 0.0);
    vec2 center = vec2(0.50 + side * (0.126 + 0.11 * low), 0.711 + 0.050 * low);
    vec2 projected = p - center;
    projected.x += projected.y * side * (0.52 + 0.48 * low);
    projected.y /= 0.46 + low * 0.08;
    float c = cos(bodyAngle);
    float s = sin(bodyAngle);
    vec2 uv = mat2(c, -s, s, c) * projected /
              (max(bodySquish, vec2(0.01)) * max(bodySize, vec2(0.01))) + 0.5;
    vec2 d = vec2(0.012, 0.021) * (0.75 + 0.75 * low);
    return 0.36 * alphaAt(uv)
         + 0.16 * (alphaAt(uv + d) + alphaAt(uv - d)
                  + alphaAt(uv + vec2(d.x, -d.y)) + alphaAt(uv + vec2(-d.x, d.y)));
}

vec4 sky(vec2 p, float side, float elevation, float visibleSun, vec3 light) {
    vec2 rail = (p - arcCenter) / arcAxes;
    float altitude = step(-0.008, -rail.y);
    float line = disc(abs(length(rail) - 1.0), 0.006) * altitude;
    float position = atan(-rail.y, -rail.x) / 3.14159265;
    float hourMark = abs(fract(position * 10.0 + 0.5) - 0.5);
    float marks = disc(hourMark, 0.036) * disc(abs(length(rail) - 1.0), 0.022) * altitude;
    vec4 outColor = over(vec4(0), vec3(0.69, 0.61, 0.44), 0.26 * max(line, marks));
    vec2 sun = arcCenter + arcAxes * vec2(-side, -elevation);
    vec2 ray = p - sun;
    float d = length(ray);
    float bearing = atan(ray.y, ray.x);
    float rays = disc(d, 0.039) * step(0.022, d) * step(0.90, cos(bearing * 8.0));
    outColor = over(outColor, light, 0.13 * disc(d, 0.060) * visibleSun);
    outColor = over(outColor, light, 0.22 * disc(d, 0.034) * visibleSun);
    outColor = over(outColor, light, 0.95 * rays * visibleSun);
    outColor = over(outColor, light, disc(d, 0.021) * visibleSun);
    outColor = over(outColor, mix(light, vec3(1.0), 0.68), disc(d, 0.014) * visibleSun);
    return outColor;
}

void main() {
    vec2 pixel = floor(qt_TexCoord0 * pixelGrid);
    vec2 p = (pixel + 0.5) / pixelGrid;
    float side = cos(sunAngle);
    float elevation = sunHeight(sunAngle);
    float lightUp = sunVisibility(elevation);
    vec3 light = sunColor(sunAngle);
    vec4 color = sky(p, side, elevation, lightUp, light);
    vec2 dial = (p - dialCenter) / dialAxes;
    float r = length(dial);
    float azimuth = atan(dial.y, dial.x) / tau;
    float hour = abs(fract(azimuth * 24.0 + 0.5) - 0.5);
    float major = abs(fract(azimuth * 6.0 + 0.5) - 0.5);
    float bodyMask = disc(length(dial - vec2(0, 0.126)), 0.994);
    float grounding = 1.0 - smoothstep(0.97, 1.14, length(dial - vec2(0, 0.19)));
    float speck = grain(pixel);
    float pit = -0.04 * step(0.945, speck) + 0.022 * step(speck, 0.08);
    vec3 edge = mix(vec3(0.15, 0.19, 0.21), vec3(0.33, 0.33, 0.27), tone(0.55 - 0.55 * dial.x * side, 5));
    float rimSeam = disc(abs(dial.y - sqrt(max(1.0 - dial.x * dial.x, 0.0)) - 0.065), 0.013);
    color = over(color, vec3(0.045, 0.050, 0.055), 0.46 * grounding);
    color = over(color, edge + pit * 0.45 - 0.075 * rimSeam, bodyMask);

    float faceMask = disc(r, 1.0);
    if (faceMask > 0.0) {
        float litSide = tone(0.58 - 0.35 * dial.x * side - 0.28 * dial.y, 7);
        vec3 rim = mix(vec3(0.32, 0.34, 0.34), vec3(0.70, 0.67, 0.55), litSide);
        vec3 enamel = mix(vec3(0.10, 0.20, 0.23), vec3(0.27, 0.38, 0.38), litSide);
        vec3 sandstone = mix(vec3(0.49, 0.44, 0.34), vec3(0.84, 0.75, 0.57), litSide);
        vec3 brass = mix(vec3(0.61, 0.43, 0.23), vec3(0.95, 0.76, 0.42), litSide);
        vec3 surface = mix(rim, enamel, disc(r, 0.951));
        surface = mix(surface, brass, disc(abs(r - 0.942), 0.007));
        surface = mix(surface, sandstone, disc(r, 0.801));
        surface = mix(surface, brass * 0.76, disc(abs(r - 0.801), 0.010));
        float tick = disc(hour, 0.063) * disc(r, 0.922) * (1.0 - disc(r, 0.861));
        float largeTick = disc(major, 0.026) * disc(r, 0.926) * (1.0 - disc(r, 0.822));
        float hourLines = disc(hour, 0.040) * disc(r, 0.762) * (1.0 - disc(r, 0.48));
        float compassRings = disc(abs(r - 0.44), 0.007) + disc(abs(r - 0.18), 0.013);
        float topBevel = disc(abs(r - 0.980), 0.011) * step(dial.y, -0.20 - dial.x * side * 0.20);
        float innerBevel = disc(abs(r - 0.785), 0.008) * step(-0.10, dial.y);
        surface = mix(surface, brass, max(tick, largeTick));
        surface = mix(surface, vec3(0.36, 0.31, 0.24), 0.61 * clamp(hourLines + compassRings, 0.0, 1.0));
        surface += pit * disc(r, 0.778) + 0.14 * topBevel + 0.063 * innerBevel;
        surface *= mix(vec3(0.52, 0.60, 0.70), mix(vec3(0.85), light, 0.30) + 0.17, lightUp);

        float shade = castShadow(qt_TexCoord0, side, elevation) * lightUp;
        surface = mix(surface, surface * vec3(0.31, 0.37, 0.48), shade * 0.96);
        color = over(color, surface, faceMask);
    }
    fragColor = color * qt_Opacity;
}
