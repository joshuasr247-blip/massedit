import { supabase } from './supabase';

/**
 * Saves user project data to Supabase.
 * Uses the `user_projects` table with columns: id, user_id, project_data, updated_at
 */
export async function saveProjectData(userId, projectData) {
  const { data, error } = await supabase
    .from('user_projects')
    .upsert(
      {
        user_id: userId,
        project_data: projectData,
        updated_at: new Date().toISOString(),
      },
      { onConflict: 'user_id' }
    )
    .select()
    .single();

  if (error) {
    console.error('Failed to save project data:', error);
    throw error;
  }
  return data;
}

/**
 * Loads user project data from Supabase.
 */
export async function loadProjectData(userId) {
  const { data, error } = await supabase
    .from('user_projects')
    .select('project_data')
    .eq('user_id', userId)
    .single();

  if (error) {
    // No data yet — that's fine for a new user
    if (error.code === 'PGRST116') return null;
    console.error('Failed to load project data:', error);
    throw error;
  }
  return data?.project_data ?? null;
}
