-- Fix for temperature_logs table recorded_at column
-- This migration ensures the recorded_at column exists and has proper index

-- Add the column if it doesn't exist (with IF NOT EXISTS logic)
DO $$
BEGIN
    -- Check if the column exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'temperature_logs' 
        AND column_name = 'recorded_at'
        AND table_schema = 'public'
    ) THEN
        -- Add the column
        ALTER TABLE public.temperature_logs 
        ADD COLUMN recorded_at timestamptz NOT NULL DEFAULT now();
        
        RAISE NOTICE 'Added recorded_at column to temperature_logs table';
    ELSE
        RAISE NOTICE 'recorded_at column already exists in temperature_logs table';
    END IF;
END $$;

-- Create index if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_temperature_logs_recorded_at 
ON public.temperature_logs (recorded_at DESC);

-- Check if zone column exists before creating the index
DO $$
BEGIN
    -- Check if the zone column exists
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'temperature_logs' 
        AND column_name = 'zone'
        AND table_schema = 'public'
    ) THEN
        -- Create the index if zone column exists
        CREATE INDEX IF NOT EXISTS idx_temperature_logs_zone 
        ON public.temperature_logs (zone, device_type);
        
        RAISE NOTICE 'Created idx_temperature_logs_zone index';
    ELSE
        RAISE NOTICE 'zone column does not exist in temperature_logs table - skipping index creation';
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_temperature_logs_created_at 
ON public.temperature_logs (created_at DESC);