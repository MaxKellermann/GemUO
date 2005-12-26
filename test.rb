$:.unshift(File.dirname($0) + '/glue')
$:.unshift(File.dirname($0))

require 'uo/client'
require 'uo/engines/collect'
require 'uo/engines/debug'
require 'uo/engines/stack'
require 'uo/engines/skills'
require 'uo/engines/stats'

raise "syntax: test.rb host port username password charname str dex int" unless ARGV.length == 8

$client = UO::Client.new(ARGV[0], ARGV[1], nil,
                         ARGV[2], ARGV[3], ARGV[4])

$stats_goal = [ARGV[5].to_i, ARGV[6].to_i, ARGV[7].to_i]

class Ingame
    def on_ingame
        #e = UO::Engines::CollectItems.new($client, 0xdf9) # collect wool
        #e = UO::Engines::CollectItems.new($client, 0x175d) # collect oil cloth

        skills = [ UO::SKILL_ANATOMY,
                   UO::SKILL_ITEM_ID,
                   UO::SKILL_ARMS_LORE,
                   #UO::SKILL_DETECT_HIDDEN,
                   UO::SKILL_EVAL_INT,
                   UO::SKILL_HIDING,
                   UO::SKILL_MUSICIANSHIP,
                   UO::SKILL_PEACEMAKING,
                   #UO::SKILL_SPIRIT_SPEAK,
                 ]
        e = UO::Engines::EasySkills.new($client, skills)
        # e = UO::Engines::StackItems.new($client, 0x1f4c) # recall scrolls

        e.start

        e = UO::Engines::StatLock.new($client, $stats_goal)
        e.start

        # UO::Engines::SimpleWalk.new($client, UO::Position.new(1410, 1735))
        # $client.timer << TestTimer.new(10)
    end
end

pos_bridge_left = UO::Position.new(1370, 1749)
pos_bridge_right = UO::Position.new(1401, 1749)
pos_left2 = UO::Position.new(1318, 1754)
pos_left2 = UO::Position.new(1303, 1748)
pos_left3 = UO::Position.new(1258, 1748)
karottenfeld1 = UO::Position.new(1237, 1738)
onionfeld1 = UO::Position.new(1205, 1698)
cottonfeld1 = UO::Position.new(1237, 1618)
pearfeld1 = UO::Position.new(1165, 1594)
cotton_eingang = UO::Position.new(4569, 1480)


$client.signal_connect(Ingame.new)
# $client.signal_connect(UO::Engines::EntityDump.new)
# $client.signal_connect(UO::Engines::WalkDump.new)
# $client.signal_connect(StatSkillJojo.new(UO::SKILL_ARMSLORE, UO::SKILL_ITEMID))

$client.run
