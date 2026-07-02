-- Migration: add shelf_life_days to products table
ALTER TABLE public.products 
ADD COLUMN IF NOT EXISTS shelf_life_days integer DEFAULT 3;

-- Update existing products to have the default shelf life of 3 days
UPDATE public.products 
SET shelf_life_days = 3 
WHERE shelf_life_days IS NULL;
