static const float PI = 3.14159265358979323846;

struct UniformBuffer
{
    float4x4 model;
    float4x4 view;
    float4x4 projection;
    uint frame_number;
}

struct RNG
{
    uint state;

    __init(uint seed)
    {
        state = seed;
    }

    __init(uint2 pixel, uint sample_index)
    {
        state = (pixel.x * 100591) ^ (pixel.y * 102191) ^ (sample_index * 103643);
    }

    [mutating]
    uint next()
    {
        const uint A = 1664525u;
        const uint C = 1013904223u;
        state = (A * state + C);
        return state;
    }

    [mutating]
    float sample_1d()
    { 
        return (next() >> 8) * 0x1p-24;
    }

    [mutating]
    float2 sample_2d()
    {
        float2 result;
        result.x = sample_1d();
        result.y = sample_1d();
        return result;
    }

    [mutating]
    float3 sample_3d()
    {
        float3 result;
        result.x = sample_1d();
        result.y = sample_1d();
        result.z = sample_1d();
        return result;
    }

    [mutating]
    float4 sample_4d()
    {
        float4 result;
        result.x = sample_1d();
        result.y = sample_1d();
        result.z = sample_1d();
        result.w = sample_1d();
        return result;
    }
}