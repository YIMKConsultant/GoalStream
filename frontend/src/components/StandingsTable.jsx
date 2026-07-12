export default function StandingsTable({ table }) {
  if (!table || table.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-white/40 border-b border-white/5 text-left">
            <th className="pb-2 pl-2 w-8">#</th>
            <th className="pb-2">Team</th>
            <th className="pb-2 text-center w-10">P</th>
            <th className="pb-2 text-center w-10">W</th>
            <th className="pb-2 text-center w-10">D</th>
            <th className="pb-2 text-center w-10">L</th>
            <th className="pb-2 text-center w-10">GD</th>
            <th className="pb-2 text-center w-12 text-green-400">Pts</th>
          </tr>
        </thead>
        <tbody>
          {table.map((row) => (
            <tr
              key={row.team.id}
              className="border-b border-white/5 hover:bg-white/5 transition-colors"
            >
              <td className="py-2 pl-2 text-white/40">{row.position}</td>
              <td className="py-2">
                <div className="flex items-center gap-2">
                  {row.team.crest && (
                    <img src={row.team.crest} alt={row.team.name} className="w-5 h-5 object-contain" />
                  )}
                  <span className="font-medium">{row.team.name}</span>
                </div>
              </td>
              <td className="py-2 text-center text-white/60">{row.playedGames}</td>
              <td className="py-2 text-center text-white/60">{row.won}</td>
              <td className="py-2 text-center text-white/60">{row.draw}</td>
              <td className="py-2 text-center text-white/60">{row.lost}</td>
              <td className="py-2 text-center text-white/60">{row.goalDifference > 0 ? `+${row.goalDifference}` : row.goalDifference}</td>
              <td className="py-2 text-center font-bold text-green-400">{row.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
